# backend/verify_neo4j_rust.py
import sys

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Check Neo4j driver
try:
    import neo4j
    print(f"✓ Neo4j driver imported successfully (version: {neo4j.__version__})")
except ImportError as e:
    print(f"✗ Failed to import Neo4j driver: {e}")

# Check Rust extension
try:
    import neo4j_rust_ext
    print(f"✓ Neo4j Rust extension imported successfully (version: {neo4j_rust_ext.__version__})")
    print(f"  Extension module path: {neo4j_rust_ext.__file__}")
    
    # Check if the module has the expected functions/classes
    extension_attrs = dir(neo4j_rust_ext)
    print(f"  Extension contains {len(extension_attrs)} attributes")
    print(f"  Sample attributes: {', '.join(sorted(extension_attrs)[:5])}...")
except ImportError as e:
    print(f"✗ Failed to import Neo4j Rust extension: {e}")

# Test Neo4j connection with Rust extension
try:
    from neo4j import GraphDatabase
    
    # This is where the Rust extension would be used if available
    print("\nTesting Neo4j connection with Rust extension:")
    uri = "bolt://localhost:7687"
    auth = ("neo4j", "devpassword")  # Update with your credentials
    
    driver = GraphDatabase.driver(uri, auth=auth)
    
    # Force initialization which will use Rust extension if available
    driver.verify_connectivity()
    print("✓ Neo4j connection successful with driver")
    
    # Execute a simple query
    with driver.session() as session:
        result = session.run("RETURN 'Connected with Rust extension' AS message")
        message = result.single()["message"]
        print(f"✓ Query result: {message}")
    
    driver.close()
except Exception as e:
    print(f"✗ Error connecting to Neo4j: {e}")