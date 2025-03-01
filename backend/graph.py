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
    populate_graph('images')