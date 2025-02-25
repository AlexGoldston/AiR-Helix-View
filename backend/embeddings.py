from sentence_transformers import SentenceTransformer
from PIL import Image
import numpy as np

class ImageEmbedder:
    def __init__(self, model_name='clip-ViT-B-32'): #default model TODO: experiment with other popular options
        self.model = SentenceTransformer(model_name)

    def get_embedding(self, image_path):
        try:
            img = Image.open(image_path)
            embedding = self.model.encode(img)
            return embedding.tolist() #convert to list for neo4j

        except Exception as e:
            print(f'error proccessing {image_path}: {e}')
            return None
            
if __name__ == '__main__':
    embedder = ImageEmbedder()
    embedding = embedder.get_embedding('images\genai-stack-support-agent-1024x576.png') #TODO: refactor for batch processing
    if embedding:
        print(f"embedding length: {len(embedding)}")
        print(f'embedding for processed image: {embedding}')
