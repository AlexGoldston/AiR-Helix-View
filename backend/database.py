import logging
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger('image-similarity')

# Global database connection
_db_instance = None

def get_db_connection():
    """Get a Neo4j database connection, creating it if necessary"""
    global _db_instance
    if _db_instance is None:
        try:
            from graph import Neo4jConnection
            _db_instance = Neo4jConnection()
            logger.info("Connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j database: {e}")
            # Create dummy DB to prevent crashes
            _db_instance = DummyDB()
            logger.warning("Using dummy database - functionality will be limited")
    return _db_instance

# Dummy database class for when Neo4j is not available
class DummyDB:
    def get_neighbors(self, *args, **kwargs):
        return {"nodes": [], "edges": []}
    
    def get_all_images(self):
        return []
    
    def get_sample_images(self, limit=10):
        return []
    
    def find_image_by_path(self, path):
        return None
    
    def count_images(self):
        return 0
    
    def remove_images(self, paths):
        return 0
    
    def clear_database(self):
        pass
    
    class DummyDriver:
        def verify_connectivity(self):
            raise Exception("No database connection")
    
    driver = DummyDriver()