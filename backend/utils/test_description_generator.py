# test_description_generator.py
import logging
import os
from image_description import get_description_generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Test directory with a few images
test_dir = "../frontend/public/images"
image_files = [os.path.join(test_dir, f) for f in os.listdir(test_dir) if f.endswith(('.jpg', '.jpeg', '.png'))][:3]

# Test ML generator
try:
    ml_generator = get_description_generator(use_ml=True)
    print(f"Using generator: {type(ml_generator).__name__}")
    
    for img in image_files:
        print(f"Image: {os.path.basename(img)}")
        if callable(ml_generator):
            desc = ml_generator(img)
        else:
            desc = ml_generator.generate_description(img)
        print(f"Description: {desc}")
        print("-" * 40)
except Exception as e:
    print(f"Error testing ML generator: {e}")

# Test basic generator
try:
    basic_generator = get_description_generator(use_ml=False)
    print(f"Using generator: {type(basic_generator).__name__}")
    
    for img in image_files:
        print(f"Image: {os.path.basename(img)}")
        desc = basic_generator(img)
        print(f"Description: {desc}")
        print("-" * 40)
except Exception as e:
    print(f"Error testing basic generator: {e}")