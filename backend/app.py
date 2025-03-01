from flask import Flask
from flask_cors import CORS
import os
import glob
import logging
import traceback
import sys

from routes.admin_routes import admin_bp
from routes.api_routes import api_bp
from routes.static_routes import static_bp
from utils.log_utils import setup_logging, log_startup_info
from utils.template_utils import ensure_template_files
from utils.image_utils import save_placeholder_image
from config import IMAGES_DIR, IMAGE_EXTENSIONS

# Import populate_graph
from graph import populate_graph

# Initialize logging
logger = setup_logging()

def create_app():
    """Create and configure the Flask application"""
    try:
        # Ensure template files exist
        ensure_template_files()
        
        # Create Flask app
        app = Flask(__name__, template_folder='templates')
        CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
        
        # Register blueprints
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
        
        return app
    
    except Exception as e:
        logger.error(f"Failed to create app: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def main():
    try:
        # Log startup information
        log_startup_info()
        
        # Create a placeholder image at startup
        save_placeholder_image()
        
        # Check for image directory
        if os.path.exists(IMAGES_DIR):
            logger.info(f"Available images in {IMAGES_DIR}:")
            image_count = 0
            image_list = []
            for ext in IMAGE_EXTENSIONS:
                image_files = glob.glob(os.path.join(IMAGES_DIR, ext))
                image_list.extend([os.path.basename(f) for f in image_files])
                image_count += len(image_files)
            
            # Log up to 10 image names
            if image_list:
                for img in image_list[:10]:
                    logger.info(f" - {img}")
                
                if len(image_list) > 10:
                    logger.info(f" ... and {len(image_list) - 10} more images")
            
            logger.info(f"Total images found: {image_count}")
        else:
            logger.warning(f"WARNING: Image directory '{IMAGES_DIR}' not found")
        
        # Attempt to import and verify database connection
        try:
            from database import get_db_connection
            db = get_db_connection()
            logger.info("Database connection verified")
            
            # Check if database is empty
            image_count = db.count_images()
            logger.info(f"Current image nodes in database: {image_count}")
            
            # Populate graph if no images exist
            if image_count == 0:
                logger.info("Database is empty. Populating graph...")
                result = populate_graph(IMAGES_DIR)
                
                if result:
                    # Verify population
                    image_count = db.count_images()
                    logger.info(f"Image nodes after population: {image_count}")
                else:
                    logger.error("Failed to populate graph")
            
            # Get sample images
            try:
                all_images = db.get_all_images()
                logger.info(f"Database contains {len(all_images)} image nodes")
                if all_images:
                    logger.info("Sample image paths:")
                    for img in all_images[:5]:
                        logger.info(f" - {img}")
            except Exception as node_error:
                logger.error(f"Error retrieving image nodes: {node_error}")
        except Exception as db_error:
            logger.error(f"Database connection failed: {db_error}")
            logger.error(traceback.format_exc())
        
        # Start the application
        app = create_app()
        logger.info("Starting Flask application...")
        
        # Use threaded mode to help with potential blocking issues
        app.run(debug=True, port=5001, threaded=True)
    
    except Exception as e:
        logger.error(f"Critical error during app startup: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()