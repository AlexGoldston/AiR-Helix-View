# test_logging.py
import time
import sys

def test_logging():
    """Test the log_startup_info function"""
    print("Testing log_startup_info...")
    
    try:
        # First, set up the logger
        print("Setting up logging...")
        from utils.log_utils import setup_logging
        logger = setup_logging()
        print("Logging setup complete")
        
        # Now try to call log_startup_info with timing
        print("Calling log_startup_info...")
        start_time = time.time()
        
        from utils.log_utils import log_startup_info
        log_startup_info()
        
        elapsed_time = time.time() - start_time
        print(f"log_startup_info completed in {elapsed_time:.2f} seconds")
        
        return True
        
    except Exception as e:
        print(f"Error during logging test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_logging()
    sys.exit(0 if success else 1)