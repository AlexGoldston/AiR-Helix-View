# test_full_embedder.py
import time
import sys

def test_full_embedder():
    """Test loading the ImageEmbedder class and model"""
    print("Testing full embedder initialization...")
    
    try:
        # Try to import and initialize the embedder
        print("Importing ImageEmbedder...")
        from embeddings import ImageEmbedder
        
        # Time the model loading
        print("Initializing embedder with model loading (this might take a while)...")
        start_time = time.time()
        
        embedder = ImageEmbedder()
        
        elapsed_time = time.time() - start_time
        print(f"Embedder initialized in {elapsed_time:.2f} seconds")
        
        print("Testing a simple embedding on a test image...")
        # You can modify this path to an actual image in your system
        # If no image is available, we'll skip this test
        import os
        test_image_path = "../frontend/public/images/allianz_stadium_sydney01.jpg"
        
        if os.path.exists(test_image_path):
            embed_start = time.time()
            embedding = embedder.get_embedding(test_image_path)
            embed_time = time.time() - embed_start
            
            if embedding:
                print(f"Successfully embedded image in {embed_time:.2f} seconds")
                print(f"Embedding length: {len(embedding)}")
            else:
                print(f"Failed to embed image after {embed_time:.2f} seconds")
        else:
            print(f"Test image not found at {test_image_path}, skipping embedding test")
        
        return True
        
    except Exception as e:
        print(f"Error during full embedder test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_embedder()
    sys.exit(0 if success else 1)