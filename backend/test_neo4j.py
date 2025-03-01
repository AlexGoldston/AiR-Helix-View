# test_neo4j.py
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import sys
import time

def test_connection():
    """Test the Neo4j database connection"""
    print("Testing Neo4j connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Get connection parameters
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "devpassword")
    
    print(f"Using Neo4j URI: {uri}")
    print(f"Username: {user}")
    print(f"Password: {'*' * len(password)}")
    
    try:
        # Set a timeout for the connection attempt
        print("Attempting to connect...")
        start_time = time.time()
        
        # Create the driver
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # Test connectivity
        driver.verify_connectivity()
        
        # If we get here, connection was successful
        elapsed_time = time.time() - start_time
        print(f"Successfully connected to Neo4j! (took {elapsed_time:.2f} seconds)")
        
        # Try a simple query
        print("Testing a simple query...")
        with driver.session() as session:
            result = session.run("RETURN 'Connection working!' AS message")
            record = result.single()
            if record:
                print(f"Query result: {record['message']}")
            
        # Close the connection
        driver.close()
        print("Connection closed")
        return True
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"Failed to connect to Neo4j after {elapsed_time:.2f} seconds")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)