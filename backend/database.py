import logging
import traceback
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import os
from dotenv import load_dotenv
import time

logger = logging.getLogger('image-similarity')

# Global database connection
_db_instance = None

def get_db_connection():
    """Get a Neo4j database connection, creating it if necessary"""
    global _db_instance
    
    # Load environment variables again to ensure they're available
    load_dotenv()
    
    if _db_instance is None:
        try:
            logger.info(f"Initializing Neo4j connection to {NEO4J_URI}")
            from graph import Neo4jConnection
            import neo4j
            _db_instance = Neo4jConnection(connection_timeout=5)
            logger.info("Connected to Neo4j database")
            
            # Test connection
            _db_instance.driver.verify_connectivity()
            logger.info("Neo4j connection verified")
        except Exception as e:
            error_msg = f"Failed to connect to Neo4j database: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Log environment details for debugging
            logger.error(f"NEO4J_URI: {NEO4J_URI}")
            logger.error(f"NEO4J_USER: {NEO4J_USER}")
            logger.error(f"Database password is {'set' if NEO4J_PASSWORD else 'not set'}")
            
            # Create dummy DB to prevent crashes
            _db_instance = DummyDB()
            logger.warning("Using dummy database - functionality will be limited")
    
    return _db_instance

# Dummy database class for when Neo4j is not available
class DummyDB:
    def __init__(self):
        logger.info("Initializing DummyDB (Neo4j unavailable)")
        self.connected = False
    
    def get_neighbors(self, *args, **kwargs):
        logger.warning("DummyDB.get_neighbors called - returning empty result")
        return {"nodes": [], "edges": []}
    
    def get_all_images(self):
        logger.warning("DummyDB.get_all_images called - returning empty list")
        return []
    
    def get_sample_images(self, limit=10):
        logger.warning("DummyDB.get_sample_images called - returning empty list")
        return []
    
    def find_image_by_path(self, path):
        logger.warning(f"DummyDB.find_image_by_path called with path={path} - returning None")
        return None
    
    def count_images(self):
        logger.warning("DummyDB.count_images called - returning 0")
        return 0
    
    def remove_images(self, paths):
        logger.warning(f"DummyDB.remove_images called with {len(paths) if isinstance(paths, list) else 1} paths - returning 0")
        return 0
    
    def clear_database(self):
        logger.warning("DummyDB.clear_database called - no action taken")
        pass
    
    def get_extended_neighbors(self, *args, **kwargs):
        logger.warning("DummyDB.get_extended_neighbors called - returning empty result")
        return {"nodes": [], "edges": []}
    
    class DummyDriver:
        def verify_connectivity(self):
            logger.warning("DummyDB.verify_connectivity called - raising exception")
            raise Exception("No database connection - using DummyDB")
    
    driver = DummyDriver()


def test_db_connection():
    """Test the database connection and return diagnostic information"""
    try:
        logger.info("Testing database connection...")
        
        # Load environment variables
        load_dotenv()
        
        # Get connection parameters
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        logger.info(f"Using Neo4j URI: {uri}")
        logger.info(f"Username: {user}")
        logger.info(f"Password is {'set' if password else 'not set'}")
        
        # Attempt to import Neo4j
        try:
            from neo4j import GraphDatabase
            logger.info("Successfully imported Neo4j GraphDatabase")
        except ImportError as e:
            logger.error(f"Failed to import Neo4j: {e}")
            return {
                "status": "ERROR",
                "error": f"Failed to import Neo4j: {e}",
                "details": traceback.format_exc()
            }
        
        # Set a timeout for the connection attempt
        start_time = time.time()
        
        # Create the driver
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info("Created Neo4j driver")
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Failed to create Neo4j driver after {elapsed_time:.2f} seconds: {e}")
            return {
                "status": "ERROR",
                "error": f"Failed to create Neo4j driver: {e}",
                "details": traceback.format_exc(),
                "elapsed_time": elapsed_time
            }
        
        # Test connectivity
        try:
            driver.verify_connectivity()
            elapsed_time = time.time() - start_time
            logger.info(f"Successfully connected to Neo4j! (took {elapsed_time:.2f} seconds)")
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Failed to connect to Neo4j after {elapsed_time:.2f} seconds: {e}")
            return {
                "status": "ERROR",
                "error": f"Failed to connect to Neo4j: {e}",
                "details": traceback.format_exc(),
                "elapsed_time": elapsed_time
            }
        
        # Try a simple query
        try:
            with driver.session() as session:
                result = session.run("RETURN 'Connection working!' AS message")
                record = result.single()
                if record:
                    logger.info(f"Query result: {record['message']}")
        except Exception as e:
            logger.error(f"Failed to run test query: {e}")
            return {
                "status": "WARNING",
                "message": "Connected to database but failed to run test query",
                "error": str(e),
                "details": traceback.format_exc(),
                "elapsed_time": time.time() - start_time
            }
        
        # Close the connection
        driver.close()
        logger.info("Connection closed")
        
        return {
            "status": "OK",
            "message": "Successfully connected to Neo4j database",
            "elapsed_time": time.time() - start_time
        }
        
    except Exception as e:
        logger.error(f"Unexpected error testing database connection: {e}")
        return {
            "status": "ERROR",
            "error": f"Unexpected error: {e}",
            "details": traceback.format_exc()
        }