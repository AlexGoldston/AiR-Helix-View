import os
import sys
import logging
import time
import argparse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('update_db.log', encoding='utf-8')  # Log file
    ]
)
logger = logging.getLogger('db-update')

def main():
    """Main function to incrementally update the database"""
    start_time = time.time()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Incrementally update the image similarity database with new images')
    parser.add_argument('--images-dir', type=str, help='Directory containing images to add (default: use configured directory)')
    parser.add_argument('--threshold', type=float, default=0.35, help='Similarity threshold (default: 0.35)')
    parser.add_argument('--no-descriptions', action='store_true', help='Skip generating descriptions for images')
    parser.add_argument('--no-ml', action='store_true', help='Avoid using ML for descriptions (use basic descriptions only)')
    parser.add_argument('--force-gpu', action='store_true', help='Force GPU usage for descriptions when available')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Make sure we're in the backend directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) != 'backend':
        backend_dir = None
        # Try to find backend directory
        if os.path.exists(os.path.join(script_dir, 'backend')):
            backend_dir = os.path.join(script_dir, 'backend')
        elif os.path.basename(os.path.dirname(script_dir)) == 'backend':
            backend_dir = os.path.dirname(script_dir)
            
        if backend_dir:
            os.chdir(backend_dir)
            logger.info(f"Changed directory to: {os.getcwd()}")
        else:
            logger.warning(f"Could not find backend directory. Current directory: {os.getcwd()}")
    
    # Load environment variables
    load_dotenv()
    logger.info("Loaded environment variables")
    
    # Import required modules after setting up environment
    try:
        # First check if the update_graph function is available
        try:
            from graph import update_graph
            logger.info("Successfully imported update_graph function")
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import update_graph function: {e}")
            logger.error("Make sure you've added the update_graph function to your graph.py file")
            return 1
            
        # Get images directory
        if args.images_dir:
            images_dir = args.images_dir
        else:
            from config import IMAGES_DIR
            images_dir = IMAGES_DIR
        
        logger.info(f"Using images directory: {images_dir}")
        
        # Check if images directory exists
        if not os.path.exists(images_dir):
            logger.error(f"Images directory does not exist: {images_dir}")
            return 1
        
        # Run the update
        logger.info(f"Starting database update with:")
        logger.info(f"  - Images dir: {images_dir}")
        logger.info(f"  - Similarity threshold: {args.threshold}")
        logger.info(f"  - Generate descriptions: {not args.no_descriptions}")
        logger.info(f"  - Use ML descriptions: {not args.no_ml}")
        logger.info(f"  - Force GPU: {args.force_gpu}")
        
        success, stats = update_graph(
            images_dir,
            similarity_threshold=args.threshold,
            generate_descriptions=not args.no_descriptions,
            use_ml_descriptions=not args.no_ml,
            force_gpu=args.force_gpu
        )
        
        elapsed_time = time.time() - start_time
        
        if success:
            initial_count = stats.get('initial_count', 0)
            added_count = stats.get('added_count', 0)
            failed_count = stats.get('failed_count', 0)
            final_count = stats.get('final_count', 0)
            new_relationships = stats.get('new_relationships', 0)
            
            logger.info("=" * 50)
            logger.info("DATABASE UPDATE COMPLETE")
            logger.info("=" * 50)
            logger.info(f"Initial image count: {initial_count}")
            logger.info(f"New images added: {added_count}")
            logger.info(f"Failed to add: {failed_count}")
            logger.info(f"Final image count: {final_count}")
            logger.info(f"New relationships created: {new_relationships}")
            logger.info(f"Total time: {elapsed_time:.2f} seconds")
            
            print("\n✅ Database update successful!")
            print(f"Added {added_count} new images with {new_relationships} new relationships")
            print(f"Total images in database: {final_count}")
            
            return 0
        else:
            error_msg = stats.get("error", "Unknown error occurred")
            logger.error(f"Database update failed: {error_msg}")
            print(f"\n❌ Database update failed: {error_msg}")
            return 1
            
    except Exception as e:
        logger.error(f"Error updating database: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())