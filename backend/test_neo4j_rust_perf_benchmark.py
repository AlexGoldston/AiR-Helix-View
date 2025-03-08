# backend/benchmark_neo4j_performance.py
from neo4j import GraphDatabase
import os
import time
import statistics
import json
from dotenv import load_dotenv

# Configuration
ITERATIONS = 10  # Number of benchmark iterations
WARMUP_ITERATIONS = 2  # Number of warmup iterations

def run_benchmark(uri, user, password, query_name, query, parameters=None):
    """Run benchmark for a specific query"""
    if parameters is None:
        parameters = {}
        
    print(f"\nRunning benchmark for: {query_name}")
    print(f"Query: {query}")
    print(f"Parameters: {parameters}")
    
    # Create driver
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # Check if Rust extension is available
    try:
        import neo4j_rust_ext
        extension_status = f"WITH Rust extension (version {neo4j_rust_ext.__version__})"
    except ImportError:
        extension_status = "WITHOUT Rust extension (using pure Python)"
    
    print(f"Neo4j driver {extension_status}")
    
    # Warm up
    print(f"Running {WARMUP_ITERATIONS} warmup iterations...")
    for i in range(WARMUP_ITERATIONS):
        with driver.session() as session:
            result = session.run(query, parameters)
            list(result)  # Consume the result
    
    # Run benchmark
    print(f"Running {ITERATIONS} benchmark iterations...")
    times = []
    for i in range(ITERATIONS):
        start_time = time.time()
        with driver.session() as session:
            result = session.run(query, parameters)
            # Consume the result
            records = list(result)
            record_count = len(records)
        
        elapsed = time.time() - start_time
        times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed:.4f} seconds ({record_count} records)")
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    median_time = statistics.median(times)
    min_time = min(times)
    max_time = max(times)
    stddev = statistics.stdev(times) if len(times) > 1 else 0
    
    # Create result object
    result = {
        "query_name": query_name,
        "extension_status": extension_status,
        "iterations": ITERATIONS,
        "average_time": avg_time,
        "median_time": median_time,
        "min_time": min_time,
        "max_time": max_time,
        "stddev": stddev,
        "times": times
    }
    
    # Print summary
    print("\nResults:")
    print(f"  Average time: {avg_time:.4f} seconds")
    print(f"  Median time: {median_time:.4f} seconds")
    print(f"  Min time: {min_time:.4f} seconds")
    print(f"  Max time: {max_time:.4f} seconds")
    print(f"  StdDev: {stddev:.4f} seconds")
    
    # Close the connection
    driver.close()
    return result

def main():
    # Load environment variables
    load_dotenv()
    
    # Get connection parameters
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "devpassword")
    
    # Define benchmark queries
    benchmarks = [
        {
            "name": "Simple Count Query",
            "query": "MATCH (n) RETURN count(n) as count"
        },
        {
            "name": "Node Retrieval",
            "query": "MATCH (n:Image) RETURN n LIMIT 50"
        },
        {
            "name": "Relationship Traversal",
            "query": "MATCH (a:Image)-[r:SIMILAR_TO]->(b:Image) RETURN a.path, r.similarity, b.path LIMIT 50"
        },
        {
            "name": "Parameterized Query",
            "query": "MATCH (a:Image {path: $imagePath})-[r:SIMILAR_TO]->(b:Image) " +
                    "WHERE r.similarity >= $threshold " +
                    "RETURN a.path, r.similarity, b.path " +
                    "ORDER BY r.similarity DESC LIMIT $limit",
            "parameters": {
                "imagePath": "allianz_stadium_sydney01.jpg",
                "threshold": 0.6,
                "limit": 10
            }
        }
    ]
    
    # Run benchmarks
    results = []
    for benchmark in benchmarks:
        parameters = benchmark.get("parameters", {})
        result = run_benchmark(uri, user, password, benchmark["name"], 
                             benchmark["query"], parameters)
        results.append(result)
    
    # Save results to file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"benchmark_results_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nBenchmark results saved to {filename}")

if __name__ == "__main__":
    main()