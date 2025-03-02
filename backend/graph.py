from neo4j import GraphDatabase
import os
import os.path as op
from dotenv import load_dotenv
from embeddings import ImageEmbedder
import numpy as np
import glob
import logging

# Configure logging
logger = logging.getLogger('image-similarity')

class Neo4jConnection:
    def __init__(self):
        load_dotenv()
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        
        logger.info(f"Attempting to connect to Neo4j at {self.uri}")
        logger.info(f"Username: {self.user}")
        
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        # Connection test
        try:
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j!")
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
                RETURN id(center) as id, center.path as path
                """
                
                center_node_result = session.run(center_node_query, image_path=image_path)
                center_node_record = center_node_result.single()
                
                if not center_node_record:
                    logger.warning(f"Center node not found with path: {image_path}")
                    return result
                    
                # Get center node details
                center_id = center_node_record['id']
                center_path = center_node_record['path']
                
                # Add center node to result
                result['nodes'].append({
                    'id': str(center_id),
                    'path': center_path,
                    'isCenter': True
                })
                
                # Find similar nodes connected to center node
                neighbors_query = """
                MATCH (center:Image {path: $image_path})-[r:SIMILAR_TO]-(neighbor:Image)
                WHERE r.similarity >= $threshold
                RETURN 
                    id(neighbor) as id, 
                    neighbor.path as path, 
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
                    similarity = record['similarity']
                    
                    # Add neighbor node
                    result['nodes'].append({
                        'id': neighbor_id,
                        'path': neighbor_path,
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
                    RETURN id(node) as id, node.path as path
                    """
                    
                    node_result = session.run(node_query, path=current_path)
                    node_record = node_result.single()
                    
                    if not node_record:
                        logger.warning(f"Node not found: {current_path}")
                        continue
                    
                    # Get node details
                    node_id = str(node_record['id'])
                    node_path = node_record['path']
                    
                    # Store node ID mapping
                    node_ids[node_path] = node_id
                    
                    # Add node to result (if not already there)
                    if not any(n['id'] == node_id for n in result['nodes']):
                        result['nodes'].append({
                            'id': node_id,
                            'path': node_path,
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
    
    def create_image_node(self, image_path, embedding):
        """Create a single image node with its embedding"""
        with self.driver.session() as session:
            try:
                result = session.execute_write(
                    self._create_image_node_tx, 
                    image_path, 
                    embedding
                )
                return result
            except Exception as e:
                logger.error(f"Error creating image node for {image_path}: {e}")
                return None
    
    @staticmethod
    def _create_image_node_tx(tx, image_path, embedding):
        try:
            query = (
                "CREATE (i:Image {path: $image_path, embedding: $embedding}) "
                "RETURN i"
            )
            result = tx.run(query, image_path=image_path, embedding=embedding)
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

def calculate_cosine_similarity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

def normalize_image_path(path):
    """Extract just the filename from any path format"""
    if path is None:
        return None
    
    # Get just the filename without any path
    return os.path.basename(path)

def populate_graph(image_dir, similarity_threshold=0.7):
    """
    Populate the Neo4j graph database with image nodes and their similarities
    
    :param image_dir: Directory containing images
    :param similarity_threshold: Minimum similarity to create a relationship
    """
    logger.info(f"Starting graph population from {image_dir}")
    logger.info(f"Similarity threshold: {similarity_threshold}")
    
    # Validate image directory
    if not os.path.exists(image_dir):
        logger.error(f"Image directory does not exist: {image_dir}")
        return False
    
    # Initialize embedder and database connection
    try:
        embedder = ImageEmbedder()
        db = Neo4jConnection()
    except Exception as e:
        logger.error(f"Failed to initialize embedder or database: {e}")
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
    
    # Process and store image embeddings
    embeddings = {}
    successful_nodes = 0
    failed_nodes = 0
    
    # First pass: generate embeddings
    for image_path in image_paths:
        try:
            # Get just the filename
            filename = normalize_image_path(image_path)
            
            # Generate embedding
            embedding = embedder.get_embedding(image_path)
            
            if embedding is not None:
                embeddings[filename] = embedding
                successful_nodes += 1
            else:
                failed_nodes += 1
                logger.warning(f"Failed to generate embedding for {filename}")
        except Exception as e:
            failed_nodes += 1
            logger.error(f"Error processing {image_path}: {e}")
    
    logger.info(f"Embeddings generated: {successful_nodes} successful, {failed_nodes} failed")
    
    # Second pass: create nodes
    for filename, embedding in embeddings.items():
        try:
            db.create_image_node(filename, embedding)
        except Exception as e:
            logger.error(f"Failed to create node for {filename}: {e}")
    
    # Third pass: create similarity relationships
    relationship_count = 0
    filenames = list(embeddings.keys())
    
    for i, filename1 in enumerate(filenames):
        for filename2 in filenames[i+1:]:
            try:
                # Calculate similarity
                similarity = calculate_cosine_similarity(
                    embeddings[filename1], 
                    embeddings[filename2]
                )
                
                # Create relationship if above threshold
                if similarity >= similarity_threshold:
                    db.create_similarity_relationship(filename1, filename2, similarity)
                    relationship_count += 1
            except Exception as e:
                logger.error(f"Error creating similarity between {filename1} and {filename2}: {e}")
    
    # Final logging
    logger.info(f"Graph population complete")
    logger.info(f"Total nodes: {len(embeddings)}")
    logger.info(f"Total relationships: {relationship_count}")
    
    # Verify database state
    node_count = db.count_images()
    logger.info(f"Nodes in database: {node_count}")
    
    # Close database connection
    db.close()
    
    return True

if __name__ == '__main__':
    # For manual testing
    populate_graph('../frontend/public/images')