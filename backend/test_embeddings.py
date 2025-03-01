# test_embedder.py
import sys
import time
from PIL import Image
import numpy as np

def test_embedder():
    """Test the SentenceTransformer embedder without loading a model"""
    print("Testing embedder import...")
    
    try:
        # First just try to import the module
        import sentence_transformers
        print(f"Successfully imported sentence_transformers version: {sentence_transformers.__version__}")
        
        # Now try to import the specific class
        from sentence_transformers import SentenceTransformer
        print("Successfully imported SentenceTransformer class")
        
        # Don't actually create a model or do embedding since that's likely 
        # where the hang is happening in the real application
        print("Import test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"Import error: {str(e)}")
        print("Make sure you've installed sentence-transformers with pip:")
        print("  pip install sentence-transformers")
        return False
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_embedder()
    sys.exit(0 if success else 1)