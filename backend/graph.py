from neo4j import GraphDatabase
import os
import os.path as op
from dotenv import load_dotenv
from embeddings import ImageEmbedder
import numpy as np

load_dotenv()

class Neo4jConnection:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

        #connection test
        try:
            self.driver.verify_connectivity()
            print("Successfully connected to Neo4j!")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            raise  # Re-raise the exception to stop execution

    def close(self):
        self.driver.close()
    
    def create_image_node(self, image_path, embedding):
        with self.driver.session() as session:
            session.execute_write(self._create_image_node_tx, image_path, embedding)
    
    @staticmethod
    def _create_image_node_tx(tx, image_path, embedding):
        query = (
            "CREATE (i:Image {path: $image_path, embedding: $embedding}) "
            "RETURN i"
        )
        result = tx.run(query, image_path=image_path, embedding=embedding)
        try:
            record = result.single()  # Get the single record
            if record:
                return {"id": record["i"].element_id, "path": record["i"]["path"]}
            else:
                return {}  # Or handle the case where no node was created
        except Exception as e:
            print(f"Failed to create image node: {e}")
            return {}
        
    def create_similarity_relationship(self, image_path1, image_path2, similarity):
        with self.driver.session() as session:
            session.execute_write(self._create_similarity_relationship_tx, image_path1, image_path2, similarity)
    
    @staticmethod
    def _create_similarity_relationship_tx(tx, image_path1, image_path2, similarity):
        query = (
            """
            MATCH (i1:Image {path: $image_path1})
            MATCH (i2: Image {path: $image_path2})
            MERGE (i1)-[r:SIMILAR_TO {similarity: $similarity}]->(i2)
            RETURN r
            """
        )
        result = tx.run(query, image_path1=image_path1, image_path2=image_path2, similarity=similarity)
        return result.single()
    
    def get_neighbors(self, image_path, similarity_threshold=0.7, limit=20):
        with self.driver.session() as session:
            return session.read_transaction(self._get_neighbors_tx, image_path, similarity_threshold, limit)
    
    @staticmethod
    def _get_neighbors_tx(tx, image_path, similarity_threshold, limit):
        # First, get the center node details
        center_query = "MATCH (i:Image {path: $image_path}) RETURN i"
        center_result = tx.run(center_query, image_path=image_path)
        center_record = center_result.single()
        
        if not center_record:
            print(f"Center node not found for path: {image_path}")
            return {"nodes": [], "edges": []}
            
        center_node = center_record["i"]
        center_id = str(center_node.element_id)
        
        print(f"Found center node: {center_node['path']} with ID: {center_id}")
        
        # Then get neighbors
        query = (
            """
            MATCH (i:Image {path: $image_path})-[r:SIMILAR_TO]->(n:Image)
            WHERE r.similarity >= $similarity_threshold
            RETURN n, r
            ORDER BY r.similarity DESC
            LIMIT $limit
            """
        )
        result = tx.run(query, image_path=image_path, similarity_threshold=similarity_threshold, limit=limit)
        
        # Format result for front end
        nodes = [{"id": center_id, "label": center_node["path"], "path": center_node["path"], "isCenter": True}]
        edges = []
        
        # Track processed nodes to avoid duplicates
        processed_nodes = {center_id}
        
        for record in result:
            neighbor = record["n"]
            relationship = record["r"]
            neighbor_id = str(neighbor.element_id)
            
            # Only add node if not already processed
            if neighbor_id not in processed_nodes:
                nodes.append({
                    "id": neighbor_id, 
                    "label": neighbor["path"], 
                    "path": neighbor["path"]
                })
                processed_nodes.add(neighbor_id)
            
            # Fix: Correct the edge source and target
            edges.append({
                "id": str(relationship.element_id), 
                "source": center_id,  # Center node is the source
                "target": neighbor_id,  # Neighbor is the target
                "weight": relationship["similarity"]
            })
        
        print(f"Returning {len(nodes)} nodes and {len(edges)} edges")
        
        return {"nodes": nodes, "edges": edges}    
    @staticmethod
    def _clear_database_tx(tx):
        tx.run("MATCH (n) DETACH DELETE n")

def calculate_cosine_similarity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

def populate_graph(image_dir, similarity_threshold=0.7):
    embedder = ImageEmbedder()
    db = Neo4jConnection()
    db.clear_database() #start with clean db for POC

    image_paths = [op.join(image_dir, f) for f in os.listdir(image_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    embeddings = {}

    #create nodes
    for image_path in image_paths:
        embedding = embedder.get_embedding(image_path)
        if embedding:
            embeddings[image_path] = embedding
            db.create_image_node(image_path, embedding)

    #create relationships
    for i, image_path1 in enumerate(image_paths):
        for j, image_path2 in enumerate(image_paths):
            if i != j: #dont compare image against itself!
                similarity = calculate_cosine_similarity(embeddings[image_path1], embeddings[image_path2])
                if similarity >= similarity_threshold:
                    db.create_similarity_relationship(image_path1, image_path2, similarity)
    
    db.close()
    print("Graph populated.")

if __name__ == '__main__':
    populate_graph('frontend\public\images')