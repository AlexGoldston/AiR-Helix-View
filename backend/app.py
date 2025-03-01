from flask import Flask
from flask_cors import CORS
import os
import glob
import logging
import traceback
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

print("Starting import of modules...")

print("Importing routes...")
from routes.admin_routes import admin_bp
from routes.api_routes import api_bp
from routes.static_routes import static_bp

print("Importing utils...")
# Import the helper functions first
from utils.image_utils import save_placeholder_image, normalize_image_path
from config import IMAGES_DIR, IMAGE_EXTENSIONS

# Initialize bare logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('app.log', encoding='utf-8')  # File output
    ]
)
logger = logging.getLogger('image-similarity')
logger.info("Basic logging initialized")

# Import graph last since it might be slow
print("Importing graph module...")
try:
    from graph import populate_graph
    print("Graph module imported successfully")
except Exception as e:
    print(f"Error importing graph module: {e}")
    logger.error(f"Error importing graph module: {e}")
    traceback.print_exc()

def run_with_timeout(func, args=None, kwargs=None, timeout=10):
    """Run a function with a timeout to prevent hanging"""
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            print(f"Function {func.__name__} timed out after {timeout} seconds")
            logger.error(f"Function {func.__name__} timed out after {timeout} seconds")
            return None

def create_app():
    """Create and configure the Flask application"""
    try:
        print("Creating Flask app...")
        
        # Create Flask app
        app = Flask(__name__, template_folder='templates')
        CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
        
        # Register blueprints
        print("Registering blueprints...")
        app.register_blueprint(admin_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(static_bp)
        
        # Detailed error handler
        @app.errorhandler(Exception)
        def handle_exception(e):
            # Log the full traceback
            logger.error(f"Unhandled exception: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": "Internal server error", "details": str(e)}, 500
        
        @app.route('/')
        def index():
            return "Image similarity API - Visit /admin for management"
        
        print("Flask app created successfully")
        return app
    
    except Exception as e:
        print(f"Failed to create app: {str(e)}")
        logger.error(f"Failed to create app: {str(e)}")
        traceback.print_exc()
        raise

def main():
    try:
        print("Starting main function...")
        logger.info("Starting main function")
        
        # Create a placeholder image at startup - this should be quick
        print("Creating placeholder image...")
        run_with_timeout(save_placeholder_image, timeout=5)
        
        # Check for image directory
        print(f"Checking image directory: {IMAGES_DIR}")
        if os.path.exists(IMAGES_DIR):
            logger.info(f"Available images in {IMAGES_DIR}")
            
            # Quick count of images instead of detailed listing
            image_count = 0
            for ext in IMAGE_EXTENSIONS:
                files = glob.glob(os.path.join(IMAGES_DIR, ext))
                image_count += len(files)
            
            logger.info(f"Total images found: {image_count}")
        else:
            logger.warning(f"WARNING: Image directory '{IMAGES_DIR}' not found")
        
        # Attempt to import and verify database connection
        print("Attempting to connect to database...")
        db = None
        try:
            from database import get_db_connection
            print("Getting database connection...")
            # Set a timeout for database connection to avoid hanging
            db = run_with_timeout(get_db_connection, timeout=10)
            
            if db:
                logger.info("Database connection verified")
                
                # Don't populate the graph on startup - it's too slow
                # Instead inform the user they need to do it manually
                image_count = db.count_images()
                logger.info(f"Current image nodes in database: {image_count}")
                
                if image_count == 0:
                    print("Database is empty. You can populate it from the admin panel.")
                    logger.info("Database is empty. Use admin panel to populate it.")
            else:
                print("Database connection timed out - proceeding with limited functionality")
                logger.warning("Database connection timed out - proceeding with limited functionality")
        except Exception as db_error:
            print(f"Database connection failed: {db_error}")
            logger.error(f"Database connection failed: {db_error}")
            traceback.print_exc()
        
        # Start the application
        print("Creating Flask application...")
        app = create_app()
        logger.info("Starting Flask application...")
        
        # Use threaded mode to help with potential blocking issues
        print("Starting Flask server...")
        app.run(debug=True, port=5001, threaded=True)
        print("Flask server started")
    
    except Exception as e:
        print(f"Critical error during app startup: {str(e)}")
        logger.error(f"Critical error during app startup: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    print("Script starting...")
    main()
    print("Script completed.")