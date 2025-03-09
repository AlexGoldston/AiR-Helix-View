#!/usr/bin/env python
# update_database_gpu.py

import os
import sys
import logging
import time
import torch
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Console output only
    ]
)
logger = logging.getLogger('db-update')

def main():
    """Main function to update the database with GPU support"""
    start_time = time.time()
    logger.info("Starting database update script with GPU support")
    
    # Check CUDA availability
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        device_count = torch.cuda.device_count()
        device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
        logger.info(f"CUDA is available! Found {device_count} device(s)")
        logger.info(f"Using GPU: {device_name}")
        
        # Set environment variables to ensure GPU usage
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Use first GPU
        os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Avoid warnings
    else:
        logger.warning("CUDA is not available. Running in CPU mode.")
    
    # Make sure we're in the backend directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) != 'backend':
        if os.path.exists(os.path.join(script_dir, 'backend')):
            os.chdir(os.path.join(script_dir, 'backend'))
            logger.info(f"Changed directory to: {os.getcwd()}")
        else:
            logger.info(f"Current directory: {os.getcwd()}")
    
    # Load environment variables
    load_dotenv()
    logger.info("Loaded environment variables")
    
    # Import required modules after setting up environment
    try:
        from config import IMAGES_DIR
        logger.info(f"Images directory: {IMAGES_DIR}")
        
        # Check if images directory exists
        if not os.path.exists(IMAGES_DIR):
            logger.error(f"Images directory does not exist: {IMAGES_DIR}")
            return 1
        
        # Count images for estimation
        import glob
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
            # Add uppercase extensions
            image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext.upper())))
        
        logger.info(f"Found {len(image_files)} image files to process")
            
        # Import database connection
        from database import get_db_connection
        logger.info("Imported database modules")
        
        # Get database connection
        db = get_db_connection()
        logger.info("Connected to database")
        
        # Clear the database
        logger.info("Clearing existing database...")
        db.clear_database()
        logger.info("Database cleared successfully")
        
        # Initialize image description generator with GPU if available
        if cuda_available:
            # First ensure transformers is using GPU
            try:
                from transformers import pipeline
                # Create a tiny test pipeline to verify GPU usage
                test_pipe = pipeline("text-classification", model="distilbert-base-uncased", device=0)
                logger.info("Verified transformers is using GPU")
                del test_pipe  # Clean up
            except Exception as e:
                logger.warning(f"Error testing GPU with transformers: {e}")
        
        # Import and call populate_graph with explicit GPU flag
        from graph import populate_graph
        logger.info("Starting database population...")
        
        # Populate the graph with images
        success = populate_graph(
            IMAGES_DIR, 
            similarity_threshold=0.7, 
            generate_descriptions=True,
            use_ml_descriptions=True,
            force_gpu=cuda_available  # Explicitly request GPU usage if available
        )
        
        if success:
            # Count images after populating
            image_count = db.count_images()
            logger.info(f"Database populated successfully with {image_count} images")
            elapsed_time = time.time() - start_time
            logger.info(f"Total time: {elapsed_time:.2f} seconds")
            return 0
        else:
            logger.error("Failed to populate database")
            return 1
            
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure you're running this script from the correct directory")
        return 1
    except Exception as e:
        logger.error(f"Error updating database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())