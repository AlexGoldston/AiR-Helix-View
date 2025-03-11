# Add this at the top of graph.py, replacing the existing import
import neo4j
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from embeddings import ImageEmbedder
import numpy as np
import glob
import logging
from utils.db_performance import track_query_performance
import traceback  # Added for better error logging
from tqdm import tqdm  # For progress tracking
from utils.feature_extraction import ImageFeatureExtractor, batch_extract_features
import json
import math

# Configure logging
logger = logging.getLogger('image-similarity')


def sanitize_for_json(obj, visited=None):
    """
    Recursively process an object to make it JSON serializable.
    Handles circular references, native Python types, etc.
    
    Args:
        obj: The object to sanitize
        visited: Set of already visited object ids (for circular reference detection)
        
    Returns:
        A JSON-serializable version of the object
    """
    if visited is None:
        visited = set()
    
    # Get object ID to detect circular references
    obj_id = id(obj)
    if obj_id in visited:
        return "CIRCULAR_REFERENCE"
    
    # Handle basic types that are already JSON serializable
    if obj is None or isinstance(obj, (int, float, str)):
        return obj
    
    # Handle booleans
    if isinstance(obj, bool):
        return obj
    
    # Add this object to visited set
    visited.add(obj_id)
    
    # Handle collections
    if isinstance(obj, list) or isinstance(obj, tuple):
        return [sanitize_for_json(item, visited.copy()) for item in obj]
    
    if isinstance(obj, dict):
        return {str(key): sanitize_for_json(value, visited.copy()) 
                for key, value in obj.items()}
    
    if isinstance(obj, set):
        return [sanitize_for_json(item, visited.copy()) for item in obj]
    
    # Handle numpy arrays
    if hasattr(obj, 'tolist'):  # For numpy arrays
        return obj.tolist()
    
    # Handle other objects - convert to string
    return str(obj)

class Neo4jConnection:
    def __init__(self, connection_timeout=5, max_connection_lifetime=3600):
        load_dotenv()
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        
        logger.info(f"Attempting to connect to Neo4j at {self.uri}")
        logger.info(f"Username: {self.user}")
        
        # Check for Neo4j Rust extension before creating driver
        rust_extension_available = False
        try:
            import neo4j_rust_ext
            rust_extension_available = True
            logger.info(f"Using Neo4j Rust extension {neo4j_rust_ext.__version__} for improved performance")
        except ImportError:
            logger.info("Neo4j Rust extension not available, using standard Python implementation")
        
        # Configure driver options
        # These optimized settings work especially well with the Rust extension
        driver_config = {
            "connection_timeout": connection_timeout,
            "max_connection_lifetime": max_connection_lifetime,
            "max_connection_pool_size": 50,  # Increased from default for better parallelism
            "connection_acquisition_timeout": 60  # Seconds to wait to acquire a connection from pool
        }
        
        # Add timeout to driver creation
        self.driver = GraphDatabase.driver(
            self.uri, 
            auth=(self.user, self.password),
            **driver_config
        )

        # Connection test with timeout
        try:
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j!")
            
            # Log driver details
            logger.info("Neo4j driver details:")
            logger.info(f"  - Driver version: {neo4j.__version__}")
            logger.info(f"  - Rust extension: {'Enabled' if rust_extension_available else 'Disabled'}")
            logger.info(f"  - Connection pool size: {driver_config['max_connection_pool_size']}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        self.driver.close()
    
    def count_images(self):
        """Count the number of image nodes in the database"""
        with self.driver.session() as session:
            result = session.run("MATCH (i:Image) RETURN count(i) as count")
            record = result.single()
            return record["count"] if record else 0
            
    def get_all_images(self):
        """Get all image paths from the database"""
        with self.driver.session() as session:
            result = session.run("MATCH (i:Image) RETURN i.path as path")
            return [record["path"] for record in result]
    
    def get_sample_images(self, limit=10):
        """Get a sample of image nodes from the database"""
        with self.driver.session() as session:
            result = session.run("MATCH (i:Image) RETURN i.path as path LIMIT $limit", limit=limit)
            return [record["path"] for record in result]
            
    def find_image_by_path(self, path):
        """Find an image node by its path"""
        with self.driver.session() as session:
            result = session.run("MATCH (i:Image {path: $path}) RETURN i", path=path)
            record = result.single()
            return record["i"]["path"] if record else None

    def count_relationships(self):
        """Count all relationships in the database"""
        with self.driver.session() as session:
            try:
                result = session.run("MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) as count")
                record = result.single()
                return record["count"] if record else 0
            except Exception as e:
                logger.error(f"Error counting relationships: {e}")
                return 0
    
    @track_query_performance(query_type="get_neighbors")
    def get_neighbors(self, image_path, similarity_threshold, limit):
        """
        Get similar image nodes and relationships based on similarity
        
        Args:
            image_path: Path to the center image
            similarity_threshold: Minimum similarity score to include (0.0-1.0)
            limit: Maximum number of neighbors to return
            
        Returns:
            Dict containing nodes and edges for graph visualization
        """
        logger.info(f"Fetching neighbors for {image_path} with threshold {similarity_threshold} and limit {limit}")
        
        # Initialize empty result
        result = {
            'nodes': [],
            'edges': []
        }
        
        try:
            with self.driver.session() as session:
                # First find the center node
                center_node_query = """
                MATCH (center:Image {path: $image_path})
                RETURN id(center) as id, center.path as path, center.description as description
                """
                
                center_node_result = session.run(center_node_query, image_path=image_path)
                center_node_record = center_node_result.single()
                
                if not center_node_record:
                    logger.warning(f"Center node not found with path: {image_path}")
                    return result
                    
                # Get center node details
                center_id = center_node_record['id']
                center_path = center_node_record['path']
                center_description = center_node_record.get('description')
                
                # Add center node to result
                result['nodes'].append({
                    'id': str(center_id),
                    'path': center_path,
                    'description': center_description,
                    'isCenter': True
                })
                
                # Find similar nodes connected to center node
                neighbors_query = """
                MATCH (center:Image {path: $image_path})-[r:SIMILAR_TO]-(neighbor:Image)
                WHERE r.similarity >= $threshold
                RETURN 
                    id(neighbor) as id, 
                    neighbor.path as path,
                    neighbor.description as description,
                    r.similarity as similarity
                ORDER BY r.similarity DESC
                LIMIT $limit
                """
                
                neighbors_result = session.run(
                    neighbors_query, 
                    image_path=image_path, 
                    threshold=similarity_threshold, 
                    limit=limit
                )
                
                # Process neighbor nodes and create edges
                edge_id = 0
                for record in neighbors_result:
                    neighbor_id = str(record['id'])
                    neighbor_path = record['path']
                    neighbor_description = record.get('description')
                    similarity = record['similarity']
                    
                    # Add neighbor node
                    result['nodes'].append({
                        'id': neighbor_id,
                        'path': neighbor_path,
                        'description': neighbor_description,
                        'isCenter': False
                    })
                    
                    # Add edge between center and neighbor
                    result['edges'].append({
                        'id': f"e{edge_id}",
                        'source': str(center_id),
                        'target': neighbor_id,
                        'weight': similarity
                    })
                    edge_id += 1
                
                logger.info(f"Found {len(result['nodes'])-1} neighbors for {image_path}")
                
        except Exception as e:
            logger.error(f"Error fetching neighbors for {image_path}: {e}")
            
        return result
    
    @track_query_performance(query_type="get_extended_neighbors")
    def get_extended_neighbors(self, image_path, similarity_threshold, depth=1, limit_per_level=10, max_nodes=100):
        """
        Get multi-level neighbor nodes for deeper graph exploration
            
            Args:
                image_path: Path to the center image
                similarity_threshold: Minimum similarity score to include (0.0-1.0)
                depth: How many levels of neighbors to explore (1=direct neighbors only, 2=neighbors of neighbors, etc.)
                limit_per_level: Maximum number of neighbors to fetch per node
                max_nodes: Overall maximum nodes to return
                
            Returns:
                Dict containing nodes and edges for graph visualization
        """
        logger.info(f"Fetching extended neighbors for {image_path} with depth {depth}")
    
        # Initialize result and tracking sets
        result = {
            'nodes': [],
            'edges': []
        }
        
        processed_nodes = set()  # Track nodes already processed
        node_queue = [(image_path, 0)]  # (path, level) tuples for BFS
        node_ids = {}  # Map of path to node ID
        
        try:
            with self.driver.session() as session:
                # Process nodes breadth-first up to max depth
                while node_queue and len(result['nodes']) < max_nodes:
                    current_path, current_level = node_queue.pop(0)
                    
                    # Skip if already processed
                    if current_path in processed_nodes:
                        continue
                    
                    # Mark as processed
                    processed_nodes.add(current_path)
                    
                    # Find node in database
                    node_query = """
                    MATCH (node:Image {path: $path})
                    RETURN id(node) as id, node.path as path, node.description as description
                    """
                    
                    node_result = session.run(node_query, path=current_path)
                    node_record = node_result.single()
                    
                    if not node_record:
                        logger.warning(f"Node not found: {current_path}")
                        continue
                    
                    # Get node details
                    node_id = str(node_record['id'])
                    node_path = node_record['path']
                    node_description = node_record.get('description')
                    
                    # Store node ID mapping
                    node_ids[node_path] = node_id
                    
                    # Add node to result (if not already there)
                    if not any(n['id'] == node_id for n in result['nodes']):
                        result['nodes'].append({
                            'id': node_id,
                            'path': node_path,
                            'description': node_description,
                            'isCenter': current_path == image_path,
                            'level': current_level
                        })
                    
                    # If we've reached max depth, don't fetch neighbors
                    if current_level >= depth:
                        continue
                    
                    # Find neighbors of this node
                    neighbors_query = """
                    MATCH (current:Image {path: $path})-[r:SIMILAR_TO]-(neighbor:Image)
                    WHERE r.similarity >= $threshold
                    RETURN 
                        id(neighbor) as id, 
                        neighbor.path as path,
                        neighbor.description as description,
                        r.similarity as similarity
                    ORDER BY r.similarity DESC
                    LIMIT $limit
                    """
                    
                    neighbors_result = session.run(
                        neighbors_query, 
                        path=current_path, 
                        threshold=similarity_threshold, 
                        limit=limit_per_level
                    )
                    
                    # Process neighbors
                    for record in neighbors_result:
                        neighbor_id = str(record['id'])
                        neighbor_path = record['path']
                        neighbor_description = record.get('description')
                        similarity = record['similarity']
                        
                        # Store neighbor ID mapping
                        node_ids[neighbor_path] = neighbor_id
                        
                        # Add neighbor to queue for next level if not processed
                        if neighbor_path not in processed_nodes:
                            node_queue.append((neighbor_path, current_level + 1))
                        
                        # Add neighbor node if not already in result
                        if not any(n['id'] == neighbor_id for n in result['nodes']):
                            result['nodes'].append({
                                'id': neighbor_id,
                                'path': neighbor_path,
                                'description': neighbor_description,
                                'isCenter': False,
                                'level': current_level + 1
                            })
                        
                        # Create unique edge ID
                        edge_id = f"e{node_id}-{neighbor_id}"
                        
                        # Add edge if not already in result
                        if not any(e['id'] == edge_id for e in result['edges']):
                            result['edges'].append({
                                'id': edge_id,
                                'source': node_id,
                                'target': neighbor_id,
                                'weight': similarity
                            })
                        
                    # Check if we've reached the max nodes
                    if len(result['nodes']) >= max_nodes:
                        logger.info(f"Reached max nodes limit: {max_nodes}")
                        break
                    
                logger.info(f"Found {len(result['nodes'])} nodes and {len(result['edges'])} edges with depth {depth}")
                
        except Exception as e:
            logger.error(f"Error fetching extended neighbors for {image_path}: {e}")
            
        return result
    
    def search_images_by_text(self, text_query, limit=10):
        """
        Search for images based on description text similarity
        
        Args:
            text_query (str): The text to search for
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of image nodes matching the query
        """
        with self.driver.session() as session:
            try:
                # Use a simple CONTAINS query
                query = """
                MATCH (i:Image)
                WHERE i.description IS NOT NULL 
                AND toLower(i.description) CONTAINS toLower($text_query)
                RETURN i.path as path, i.description as description, id(i) as id
                LIMIT $limit
                """
                
                result = session.run(query, text_query=text_query, limit=limit)
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Error searching images by text: {e}")
                return []
        
    def remove_images(self, image_paths):
        """Remove image nodes and their relationships"""
        with self.driver.session() as session:
            return session.execute_write(self._remove_images_tx, image_paths)
    
    @staticmethod
    def _remove_images_tx(tx, image_paths):
        # Convert to list if it's not already
        if not isinstance(image_paths, list):
            image_paths = [image_paths]
            
        # Execute the query to remove nodes and relationships
        result = tx.run(
            """
            UNWIND $paths AS path
            MATCH (i:Image {path: path})
            DETACH DELETE i
            RETURN count(i) as count
            """,
            paths=image_paths
        )
        
        record = result.single()
        return record["count"] if record else 0
    
    def create_image_node(self, image_path, embedding, description=None):
        """Create a single image node with its embedding and description"""
        with self.driver.session() as session:
            try:
                result = session.execute_write(
                    self._create_image_node_tx, 
                    image_path, 
                    embedding,
                    description
                )
                return result
            except Exception as e:
                logger.error(f"Error creating image node for {image_path}: {e}")
                return None
    
    @staticmethod
    def _create_image_node_tx(tx, image_path, embedding, description=None):
        try:
            query = (
                "CREATE (i:Image {path: $image_path, embedding: $embedding, description: $description}) "
                "RETURN i"
            )
            result = tx.run(query, image_path=image_path, embedding=embedding, description=description)
            record = result.single()
            return {"id": record["i"].element_id, "path": record["i"]["path"]} if record else None
        except Exception as e:
            logger.error(f"Transaction error creating node: {e}")
            raise
        
    def create_similarity_relationship(self, image_path1, image_path2, similarity):
        """Create a similarity relationship between two image nodes"""
        with self.driver.session() as session:
            try:
                result = session.execute_write(
                    self._create_similarity_relationship_tx, 
                    image_path1, 
                    image_path2, 
                    similarity
                )
                return result
            except Exception as e:
                logger.error(f"Error creating similarity between {image_path1} and {image_path2}: {e}")
                return None
    
    @staticmethod
    def _create_similarity_relationship_tx(tx, image_path1, image_path2, similarity):
        query = (
            """
            MATCH (i1:Image {path: $image_path1})
            MATCH (i2:Image {path: $image_path2})
            MERGE (i1)-[r:SIMILAR_TO {similarity: $similarity}]->(i2)
            RETURN r
            """
        )
        result = tx.run(query, image_path1=image_path1, image_path2=image_path2, similarity=similarity)
        return result.single()
    
    def clear_database(self):
        """Clear all nodes and relationships from the database"""
        logger.info("Clearing entire database...")
        with self.driver.session() as session:
            session.execute_write(self._clear_database_tx)
            logger.info("Database cleared")

    @staticmethod
    def _clear_database_tx(tx):
        tx.run("MATCH (n) DETACH DELETE n")

    def create_schema_constraints(self):
        """Create constraints and indexes for faster lookups"""
        with self.driver.session() as session:
            # Create constraints for unique nodes
            try:
                session.run("CREATE CONSTRAINT FOR (t:Tag) REQUIRE t.name IS UNIQUE")
                session.run("CREATE CONSTRAINT FOR (c:Category) REQUIRE c.name IS UNIQUE")
                
                # Create indexes for faster lookups
                session.run("CREATE INDEX FOR (i:Image) ON (i.path)")
                session.run("CREATE INDEX FOR (f:Feature) ON (f.name, f.value)")
                
                logger.info("Created constraints and indexes for tags and features")
            except Exception as e:
                # Handle case where constraints already exist
                logger.info(f"Schema setup note: {e}")

    def store_image_features(self, image_path, features):
        """
        Store extracted image features in the graph database
        
        Args:
            image_path (str): Path of the image
            features (dict): Dictionary of extracted features
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not features:
            logger.warning(f"No features to store for {image_path}")
            return False
            
        with self.driver.session() as session:
            try:
                # Store features as a transaction
                return session.execute_write(self._store_image_features_tx, image_path, features)
            except Exception as e:
                logger.error(f"Error storing features for {image_path}: {e}")
                return False

    @staticmethod
    def _store_image_features_tx(tx, image_path, features):
        """Transaction function to store image features"""
        
        # First check if the image node exists
        result = tx.run(
            "MATCH (i:Image {path: $path}) RETURN i",
            path=image_path
        )
        
        if not result.single():
            # Image node not found
            return False
        
        # 1. Store feature properties on the Image node itself
        # For properties that are simple values, store directly on the image node
        feature_props = {}
        
        # Add basic properties
        if 'basic' in features:
            for key, value in features['basic'].items():
                feature_props[f"basic_{key}"] = value
        
        # Add average color as property
        if 'color' in features and 'color_hex' in features['color']:
            feature_props["color_hex"] = features['color']['color_hex']
        
        if 'color' in features and 'brightness_category' in features['color']:
            feature_props["brightness"] = features['color']['brightness_category']
        
        # Store properties if we have any
        if feature_props:
            props_str = ", ".join(f"i.{key} = ${key}" for key in feature_props.keys())
            query = f"MATCH (i:Image {{path: $path}}) SET {props_str} RETURN i"
            props = {**feature_props, "path": image_path}
            tx.run(query, **props)
        
        # 2. Store complex features as serialized JSON
        if features:
            # Serialize the features dictionary to JSON
            sanitized_features = sanitize_for_json(features)
            features_json = json.dumps(sanitized_features)
            tx.run(
                """
                MATCH (i:Image {path: $path})
                SET i.features_json = $features_json
                """,
                path=image_path,
                features_json=features_json
            )
        
        # 3. Create Tag nodes and connect them to the image
        if 'tags' in features and features['tags']:
            for tag in features['tags']:
                # Handle hierarchical tags (e.g., "contains:person")
                if ':' in tag:
                    category, value = tag.split(':', 1)
                    
                    # Create or match the category node
                    tx.run(
                        """
                        MERGE (c:Category {name: $category})
                        MERGE (t:Tag {name: $tag})
                        MERGE (t)-[:IN_CATEGORY]->(c)
                        MERGE (i:Image {path: $path})
                        MERGE (i)-[:HAS_TAG]->(t)
                        """,
                        category=category,
                        tag=tag,
                        path=image_path
                    )
                else:
                    # Simple tag without category
                    tx.run(
                        """
                        MERGE (t:Tag {name: $tag})
                        MERGE (i:Image {path: $path})
                        MERGE (i)-[:HAS_TAG]->(t)
                        """,
                        tag=tag,
                        path=image_path
                    )
        
        # 4. Store specific feature types as separate nodes
        
        # Colors
        if 'color' in features and 'dominant_colors' in features['color']:
            for color in features['color']['dominant_colors']:
                tx.run(
                    """
                    MERGE (c:Color {name: $color})
                    MERGE (i:Image {path: $path})
                    MERGE (i)-[:HAS_COLOR]->(c)
                    """,
                    color=color,
                    path=image_path
                )
        
        # Detected objects
        if 'objects' in features:
            for obj in features['objects']:
                if 'label' in obj and 'confidence' in obj:
                    tx.run(
                        """
                        MERGE (o:Object {name: $label})
                        MERGE (i:Image {path: $path})
                        MERGE (i)-[r:CONTAINS]->(o)
                        SET r.confidence = $confidence
                        """,
                        label=obj['label'],
                        path=image_path,
                        confidence=obj['confidence']
                    )
        
        # EXIF data for camera equipment
        if 'exif' in features:
            exif = features['exif']
            
            # Camera model
            if 'camera_model' in exif:
                tx.run(
                    """
                    MERGE (c:Camera {model: $model})
                    MERGE (i:Image {path: $path})
                    MERGE (i)-[:TAKEN_WITH]->(c)
                    """,
                    model=exif['camera_model'],
                    path=image_path
                )
            
            # Lens
            if 'lens' in exif:
                tx.run(
                    """
                    MERGE (l:Lens {name: $lens})
                    MERGE (i:Image {path: $path})
                    MERGE (i)-[:USED_LENS]->(l)
                    """,
                    lens=exif['lens'],
                    path=image_path
                )
        
        return True

    def get_images_by_tags(self, tags, operator='AND', limit=50):
        """
        Find images that have specific tags
        
        Args:
            tags (list): List of tags to search for
            operator (str): 'AND' or 'OR' - whether all tags must match or any
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of image paths that match the criteria
        """
        if not tags:
            return []
        
        with self.driver.session() as session:
            try:
                if operator.upper() == 'AND':
                    # All tags must match
                    query = """
                    MATCH (i:Image)
                    WHERE all(tag IN $tags WHERE EXISTS((i)-[:HAS_TAG]->(:Tag {name: tag})))
                    RETURN i.path AS path
                    LIMIT $limit
                    """
                else:  # OR
                    # Any tag must match
                    query = """
                    MATCH (i:Image)-[:HAS_TAG]->(t:Tag)
                    WHERE t.name IN $tags
                    RETURN DISTINCT i.path AS path
                    LIMIT $limit
                    """
                
                result = session.run(query, tags=tags, limit=limit)
                return [record["path"] for record in result]
            except Exception as e:
                logger.error(f"Error finding images by tags: {e}")
                return []

    def get_images_by_color(self, color, limit=50):
        """
        Find images with a specific dominant color
        
        Args:
            color (str): Color name to search for
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of image paths that match the criteria
        """
        with self.driver.session() as session:
            try:
                query = """
                MATCH (i:Image)-[:HAS_COLOR]->(c:Color {name: $color})
                RETURN i.path AS path
                LIMIT $limit
                """
                
                result = session.run(query, color=color, limit=limit)
                return [record["path"] for record in result]
            except Exception as e:
                logger.error(f"Error finding images by color: {e}")
                return []

    def get_images_containing_object(self, object_name, min_confidence=0.5, limit=50):
        """
        Find images containing a specific object
        
        Args:
            object_name (str): Name of the object to search for
            min_confidence (float): Minimum confidence score
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of image paths that match the criteria
        """
        with self.driver.session() as session:
            try:
                query = """
                MATCH (i:Image)-[r:CONTAINS]->(o:Object {name: $object_name})
                WHERE r.confidence >= $min_confidence
                RETURN i.path AS path, r.confidence AS confidence
                ORDER BY r.confidence DESC
                LIMIT $limit
                """
                
                result = session.run(
                    query, 
                    object_name=object_name, 
                    min_confidence=min_confidence,
                    limit=limit
                )
                
                return [{"path": record["path"], "confidence": record["confidence"]} for record in result]
            except Exception as e:
                logger.error(f"Error finding images containing object: {e}")
                return []

    def search_images_by_features(self, criteria, limit=50):
        """
        Search for images based on multiple feature criteria
        
        Args:
            criteria (dict): Dictionary of search criteria
                Example:
                {
                    "tags": ["landscape", "sunset"],
                    "tags_operator": "AND",
                    "colors": ["blue", "orange"],
                    "colors_operator": "OR",
                    "objects": ["person", "dog"],
                    "objects_operator": "OR",
                    "min_confidence": 0.6,
                    "orientation": "landscape",
                    "camera": "Canon EOS R5"
                }
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of image paths that match the criteria
        """
        if not criteria:
            return []
        
        with self.driver.session() as session:
            try:
                # Build a Cypher query based on the criteria
                match_clauses = ["MATCH (i:Image)"]
                where_clauses = []
                params = {}
                
                # Handle tags
                if "tags" in criteria and criteria["tags"]:
                    tags = criteria["tags"]
                    params["tags"] = tags
                    
                    if criteria.get("tags_operator", "AND").upper() == "AND":
                        # All tags must match
                        where_clauses.append(
                            "all(tag IN $tags WHERE EXISTS((i)-[:HAS_TAG]->(:Tag {name: tag})))"
                        )
                    else:
                        # Any tag must match
                        match_clauses.append("MATCH (i)-[:HAS_TAG]->(tag:Tag)")
                        where_clauses.append("tag.name IN $tags")
                
                # Handle colors
                if "colors" in criteria and criteria["colors"]:
                    colors = criteria["colors"]
                    params["colors"] = colors
                    
                    if criteria.get("colors_operator", "OR").upper() == "AND":
                        # All colors must be present
                        where_clauses.append(
                            "all(color IN $colors WHERE EXISTS((i)-[:HAS_COLOR]->(:Color {name: color})))"
                        )
                    else:
                        # Any color must be present
                        match_clauses.append("MATCH (i)-[:HAS_COLOR]->(color:Color)")
                        where_clauses.append("color.name IN $colors")
                
                # Handle objects
                if "objects" in criteria and criteria["objects"]:
                    objects = criteria["objects"]
                    min_confidence = criteria.get("min_confidence", 0.5)
                    params["objects"] = objects
                    params["min_confidence"] = min_confidence
                    
                    if criteria.get("objects_operator", "OR").upper() == "AND":
                        # All objects must be present
                        where_clauses.append(
                            """all(obj IN $objects WHERE EXISTS((i)-[r:CONTAINS]->(:Object {name: obj}))
                            AND any(r in [(i)-[rel:CONTAINS]->(:Object {name: obj}) | rel] 
                            WHERE r.confidence >= $min_confidence))"""
                        )
                    else:
                        # Any object must be present
                        match_clauses.append("MATCH (i)-[r:CONTAINS]->(obj:Object)")
                        where_clauses.append(
                            "obj.name IN $objects AND r.confidence >= $min_confidence"
                        )
                
                # Handle orientation
                if "orientation" in criteria and criteria["orientation"]:
                    orientation = criteria["orientation"]
                    params["orientation"] = orientation
                    where_clauses.append("i.basic_orientation = $orientation")
                
                # Handle camera
                if "camera" in criteria and criteria["camera"]:
                    camera = criteria["camera"]
                    params["camera"] = camera
                    match_clauses.append("MATCH (i)-[:TAKEN_WITH]->(camera:Camera)")
                    where_clauses.append("camera.model = $camera")
                
                # Build the final query
                query = "\n".join(match_clauses)
                
                if where_clauses:
                    query += "\nWHERE " + " AND ".join(where_clauses)
                
                query += "\nRETURN DISTINCT i.path AS path LIMIT $limit"
                params["limit"] = limit
                
                # Execute the query
                result = session.run(query, **params)
                return [record["path"] for record in result]
                
            except Exception as e:
                logger.error(f"Error searching images by features: {e}")
                logger.error(f"Query error details: {traceback.format_exc()}")
                return []

def calculate_cosine_similarity(embedding1, embedding2):
    """
    Calculate cosine similarity between two embeddings
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
    
    Returns:
        float: Similarity score between 0 and 1
    """
    try:
        similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
        
        # Ensure the result is between 0 and 1
        similarity = max(0.0, min(1.0, similarity))
        
        # Log high similarities for debugging
        if similarity > 0.5:
            logger.debug(f"High similarity found: {similarity:.4f}")
            
        return similarity
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return 0.0  # Return 0 similarity on error


def normalize_image_path(path):
    """Extract just the filename from any path format"""
    if path is None:
        return None
    
    # Get just the filename without any path
    return os.path.basename(path)

def extract_and_store_features(image_dir, db_connection, use_ml_features=True):
        logger.info("Setting up database schema for features and tags")
        db_connection.create_schema_constraints()
        # Find all image files
        image_paths = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            image_paths.extend(glob.glob(os.path.join(image_dir, ext)))
            image_paths.extend(glob.glob(os.path.join(image_dir, ext.upper())))
        
        logger.info(f"Extracting features for {len(image_paths)} images")
        
        # Use batch processing for efficiency
        batch_size = 10  # Adjust based on your system's capabilities
        
        # Track progress
        processed_count = 0
        successful_count = 0
        
        # Process in batches
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{math.ceil(len(image_paths)/batch_size)} ({len(batch)} images)")
            
            # Extract features for the batch
            extractor = ImageFeatureExtractor(use_ml_features=use_ml_features)
            
            for image_path in tqdm(batch, desc="Extracting features"):
                try:
                    # Get normalized filename
                    filename = normalize_image_path(image_path)
                    
                    # Extract features
                    features = extractor.extract_features(image_path)
                    
                    if features:
                        # Store features in database
                        success = db_connection.store_image_features(filename, features)
                        
                        if success:
                            successful_count += 1
                        
                    processed_count += 1
                    
                    # Log progress periodically
                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count}/{len(image_paths)} images, {successful_count} successful")
                    
                except Exception as e:
                    logger.error(f"Error processing {image_path}: {e}")
                    logger.error(traceback.format_exc())
        
        logger.info(f"Feature extraction complete. Processed {processed_count} images, {successful_count} successful.")
        return successful_count

def populate_graph(image_dir, similarity_threshold=0.35, generate_descriptions=True, use_ml_descriptions=True, force_gpu=False):
    """
    Populate the Neo4j graph database with image nodes and their similarities
    
    Args:
        image_dir (str): Directory containing images
        similarity_threshold (float): Minimum similarity to create a relationship (lower value = more connections)
        generate_descriptions (bool): Whether to generate descriptions for images
        use_ml_descriptions (bool): Whether to use ML-based descriptions when available
        force_gpu (bool): Whether to force GPU usage for descriptions if available
    """
    logger.info(f"Starting graph population from {image_dir}")
    logger.info(f"Similarity threshold: {similarity_threshold}")
    logger.info(f"Generate descriptions: {generate_descriptions}")
    logger.info(f"Use ML descriptions: {use_ml_descriptions}")
    logger.info(f"Force GPU usage: {force_gpu}")
    
    # Validate image directory
    if not os.path.exists(image_dir):
        logger.error(f"Image directory does not exist: {image_dir}")
        return False
    
    # Initialize embedder and database connection
    try:
        embedder = ImageEmbedder()
        db = Neo4jConnection()
        
        # Initialize description generator if needed
        description_generator = None
        if generate_descriptions:
            # Import the description generator
            try:
                from utils.image_description import get_description_generator
                # Pass both parameters to get_description_generator
                description_generator = get_description_generator(use_ml=use_ml_descriptions, force_gpu=force_gpu)
                logger.info(f"Using {'ML-based' if use_ml_descriptions else 'basic'} description generator")
                if force_gpu:
                    logger.info("GPU usage requested for image descriptions")
                    
                # Test the description generator
                if description_generator:
                    try:
                        # Find a sample image to test
                        sample_images = glob.glob(os.path.join(image_dir, '*.jpg'))
                        if sample_images:
                            test_image = sample_images[0]
                            logger.info(f"Testing description generator with image: {test_image}")
                            
                            if callable(description_generator):
                                test_desc = description_generator(test_image)
                            else:
                                test_desc = description_generator.generate_description(test_image)
                                
                            logger.info(f"Test description: {test_desc}")
                    except Exception as test_error:
                        logger.error(f"Description generator test failed: {test_error}")
                        logger.error(traceback.format_exc())
            except Exception as e:
                logger.warning(f"Failed to initialize description generator: {e}")
                logger.warning(traceback.format_exc())
                logger.warning("Descriptions will not be generated")
                description_generator = None
    except Exception as e:
        logger.error(f"Failed to initialize embedder or database: {e}")
        logger.error(traceback.format_exc())
        return False
    
    # Clear existing database
    try:
        db.clear_database()
        logger.info("Existing database cleared")
    except Exception as e:
        logger.error(f"Failed to clear database: {e}")
        return False
    
    # Find all image files
    image_paths = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
        image_paths.extend(glob.glob(os.path.join(image_dir, ext)))
        image_paths.extend(glob.glob(os.path.join(image_dir, ext.upper())))
    
    logger.info(f"Found {len(image_paths)} images to process")
    
    # Track specific images of interest (for debugging)
    important_images = ["allianz_stadium_sydney01.jpg", "allianz_field04.jpg"]
    important_image_found = False
    
    # Check if important images exist in the directory
    for img_path in image_paths:
        filename = normalize_image_path(img_path)
        if filename in important_images:
            important_image_found = True
            logger.info(f"Found important image: {filename}")
    
    if not important_image_found:
        logger.warning(f"Could not find any of the important images: {important_images}")
        logger.warning("This may cause issues when using these images as center nodes")
    
    # Process and store image embeddings
    embeddings = {}
    descriptions = {}
    successful_nodes = 0
    failed_nodes = 0
    
    # First pass: generate embeddings (separate from descriptions for better organization)
    for image_path in tqdm(image_paths, desc="Generating embeddings"):
        try:
            # Get just the filename
            filename = normalize_image_path(image_path)
            
            # Generate embedding
            embedding = embedder.get_embedding(image_path)
            
            if embedding is not None:
                embeddings[filename] = embedding
                successful_nodes += 1
                
                # Log if this is an important image
                if filename in important_images:
                    logger.info(f"Generated embedding for important image: {filename}")
            else:
                failed_nodes += 1
                logger.warning(f"Failed to generate embedding for {filename}")
        except Exception as e:
            failed_nodes += 1
            logger.error(f"Error processing {image_path}: {e}")
            logger.error(traceback.format_exc())
    
    logger.info(f"Embeddings generated: {successful_nodes} successful, {failed_nodes} failed")
    
    # Second pass: generate descriptions
    if generate_descriptions and description_generator:
        # Check if the description generator supports batch processing
        has_batch_support = hasattr(description_generator, 'generate_descriptions_batch')
        
        if has_batch_support and not callable(description_generator):
            # Use batch processing for ML-based descriptions
            logger.info("Using batch processing for descriptions")
            
            # Get paths for images that have embeddings
            valid_image_paths = []
            path_to_filename = {}  # Map from full path to normalized filename
            
            for image_path in image_paths:
                filename = normalize_image_path(image_path)
                if filename in embeddings:
                    valid_image_paths.append(image_path)
                    path_to_filename[image_path] = filename
            
            # Define optimal batch size based on available GPU memory
            # Smaller batch size for larger images, larger for smaller images
            batch_size = 8  # Default value, adjust based on your GPU memory
            
            # Process in batches
            logger.info(f"Processing {len(valid_image_paths)} images in batches of {batch_size}")
            
            try:
                # Generate descriptions in batches
                batch_results = description_generator.generate_descriptions_batch(
                    valid_image_paths, 
                    batch_size=batch_size,
                    max_length=50
                )
                
                # Convert to our format (filename -> description)
                for full_path, desc in batch_results.items():
                    filename = path_to_filename.get(full_path) or normalize_image_path(full_path)
                    if filename and desc:
                        descriptions[filename] = desc
                
                logger.info(f"Generated {len(descriptions)} descriptions using batch processing")
                
            except Exception as batch_error:
                logger.error(f"Batch description generation failed: {batch_error}")
                logger.error(traceback.format_exc())
                logger.warning("Falling back to individual processing")
                
                # Fallback to individual processing
                for image_path in tqdm(valid_image_paths, desc="Generating descriptions (fallback)"):
                    try:
                        filename = normalize_image_path(image_path)
                        
                        # Generate description
                        if callable(description_generator):
                            description = description_generator(image_path)
                        else:
                            description = description_generator.generate_description(image_path)
                        
                        if description:
                            descriptions[filename] = description
                    except Exception as e:
                        logger.error(f"Error generating description for {filename}: {e}")
                
        else:
            # Process descriptions individually (for basic description function or when batch not supported)
            logger.info("Using individual processing for descriptions")
            
            for image_path in tqdm(image_paths, desc="Generating descriptions"):
                try:
                    filename = normalize_image_path(image_path)
                    
                    # Skip if embedding generation failed
                    if filename not in embeddings:
                        continue
                    
                    # Generate description
                    if callable(description_generator):
                        description = description_generator(image_path)
                    else:
                        description = description_generator.generate_description(image_path)
                    
                    if description:
                        descriptions[filename] = description
                        # Log a snippet of the description to avoid cluttering logs
                        logger.debug(f"Generated description for {filename}: {description[:50]}...")
                except Exception as e:
                    logger.error(f"Error generating description for {filename}: {e}")
                    logger.error(traceback.format_exc())
    
    logger.info(f"Descriptions generated: {len(descriptions)}")
    
    # Third pass: create nodes
    for filename, embedding in tqdm(embeddings.items(), desc="Creating nodes"):
        try:
            # Get description if available
            description = descriptions.get(filename)
            db.create_image_node(filename, embedding, description)
            
            # Log if this is an important image
            if filename in important_images:
                logger.info(f"Created node for important image: {filename}")
        except Exception as e:
            logger.error(f"Failed to create node for {filename}: {e}")

    if generate_descriptions:
        logger.info("Extracting and storing image features...")
        try:
            extract_and_store_features(image_dir, db, use_ml_features=True)
        except Exception as e:
            logger.error(f"Error during feature extraction: {e}")
            logger.error(traceback.format_exc())
            # Continue even if feature extraction fails
        
    # Fourth pass: create similarity relationships
    relationship_count = 0
    center_node_relationships = 0  # Counter for relationships involving important images
    filenames = list(embeddings.keys())
    
    logger.info("Creating similarity relationships...")
    for i, filename1 in enumerate(tqdm(filenames, desc="Creating relationships")):
        # Track relationships for important center nodes
        has_relationships = False
        
        for filename2 in filenames[i+1:]:
            try:
                # Calculate similarity
                similarity = calculate_cosine_similarity(
                    embeddings[filename1], 
                    embeddings[filename2]
                )
                
                # Log similarities involving important images
                if filename1 in important_images or filename2 in important_images:
                    logger.info(f"Similarity between {filename1} and {filename2}: {similarity:.4f}")
                
                # Create relationship if above threshold
                if similarity >= similarity_threshold:
                    db.create_similarity_relationship(filename1, filename2, similarity)
                    relationship_count += 1
                    
                    # Track relationships for important images
                    if filename1 in important_images or filename2 in important_images:
                        center_node_relationships += 1
                        has_relationships = True
                        logger.info(f"Created relationship: {filename1} - {filename2} ({similarity:.4f})")
            except Exception as e:
                logger.error(f"Error creating similarity between {filename1} and {filename2}: {e}")
        
        # Log if an important image has no relationships
        if filename1 in important_images and not has_relationships:
            logger.warning(f"Important image {filename1} has no relationships with similarity threshold {similarity_threshold}")
    
    # Final logging
    logger.info("Graph population complete")
    logger.info(f"Total nodes: {len(embeddings)}")
    logger.info(f"Total relationships: {relationship_count}")
    logger.info(f"Relationships for important images: {center_node_relationships}")
    
    # Verify database state
    node_count = db.count_images()
    logger.info(f"Nodes in database: {node_count}")
    
    # Close database connection
    db.close()
    
    return True

if __name__ == '__main__':
    # For manual testing
    populate_graph('../frontend/public/images', generate_descriptions=True, use_ml_descriptions=True)