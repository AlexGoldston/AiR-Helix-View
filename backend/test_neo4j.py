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
    
    # Check if Rust extension is available
    try:
        import neo4j_rust_ext
        print(f"Neo4j Rust extension detected (version {neo4j_rust_ext.__version__})")
        print(f"Extension location: {neo4j_rust_ext.__file__}")
    except ImportError as e:
        print(f"Neo4j Rust extension not found: {e}")
        print("Using pure Python implementation")
    
    try:
        # Set a timeout for the connection attempt
        print("Attempting to connect...")
        start_time = time.time()
        
        # Create the driver with optimized configuration
        driver = GraphDatabase.driver(
            uri, 
            auth=(user, password),
            connection_timeout=5,
            max_connection_lifetime=3600,
            max_connection_pool_size=50
        )
        
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
        
        # Run a benchmark query to test performance
        print("\nRunning benchmark query...")
        benchmark_times = []
        benchmark_query = "MATCH (n) RETURN count(n) as count"
        
        # Warmup
        with driver.session() as session:
            session.run(benchmark_query).single()
        
        # Actual benchmark
        for i in range(5):
            start = time.time()
            with driver.session() as session:
                result = session.run(benchmark_query)
                count = result.single()["count"]
            end = time.time()
            benchmark_times.append(end - start)
            print(f"  Run {i+1}: {benchmark_times[-1]:.4f} seconds (count: {count})")
        
        avg_time = sum(benchmark_times) / len(benchmark_times)
        print(f"Average query time: {avg_time:.4f} seconds")
            
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