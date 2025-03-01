# test_logging_step_by_step.py
import logging
import os
import sys
import time
import platform
from config import IMAGES_DIR, NEO4J_URI, LOG_LEVEL

def setup_basic_logger():
    """Setup a very basic logger for testing"""
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger('test-logger')

def test_log_startup_step_by_step():
    """Test each part of log_startup_info separately"""
    logger = setup_basic_logger()
    
    print("1. Basic logging test...")
    logger.info("Test message")
    print("✓ Basic logging works")
    
    print("2. Logging system info...")
    try:
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {platform.platform()}")
        logger.info(f"Current working directory: {os.getcwd()}")
        print("✓ System info logging works")
    except Exception as e:
        print(f"✗ Error logging system info: {e}")
    
    print("3. Checking IMAGES_DIR...")
    try:
        print(f"Images directory path: {IMAGES_DIR}")
        if os.path.exists(IMAGES_DIR):
            print(f"✓ Images directory exists: {IMAGES_DIR}")
        else:
            print(f"✗ Images directory does not exist: {IMAGES_DIR}")
    except Exception as e:
        print(f"✗ Error checking images directory: {e}")
    
    print("4. Testing directory listing (without glob)...")
    try:
        if os.path.exists(IMAGES_DIR):
            files = os.listdir(IMAGES_DIR)
            print(f"Found {len(files)} files in directory")
            print(f"First few files: {files[:5] if len(files) > 5 else files}")
        else:
            print("Images directory doesn't exist, skipping listdir test")
    except Exception as e:
        print(f"✗ Error listing directory: {e}")
    
    print("5. Testing glob operation...")
    try:
        import glob
        print("Imported glob module")
        
        if os.path.exists(IMAGES_DIR):
            start_time = time.time()
            
            print("Searching for jpg files...")
            jpg_files = glob.glob(os.path.join(IMAGES_DIR, "*.jpg"))
            print(f"Found {len(jpg_files)} jpg files in {time.time() - start_time:.2f} seconds")
            
            print("Searching for all image types...")
            all_images = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
                start_time = time.time()
                files = glob.glob(os.path.join(IMAGES_DIR, ext))
                all_images.extend(files)
                print(f"Found {len(files)} {ext} files in {time.time() - start_time:.2f} seconds")
                
                # Also check uppercase extensions
                files = glob.glob(os.path.join(IMAGES_DIR, ext.upper()))
                all_images.extend(files)
                print(f"Found {len(files)} {ext.upper()} files")
            
            print(f"Total images found: {len(all_images)}")
        else:
            print("Images directory doesn't exist, skipping glob test")
    except Exception as e:
        print(f"✗ Error in glob operation: {e}")
    
    print("All tests completed!")

if __name__ == "__main__":
    test_log_startup_step_by_step()