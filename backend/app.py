from flask import Flask, send_from_directory
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

def create_app():
    """Create and configure the Flask application"""
    try:
        print("Creating Flask app...")
        
        # Create Flask app
        app = Flask(__name__, 
                    template_folder='templates', 
                    static_folder=os.path.join('..', 'frontend', 'public', 'images'),
                    static_url_path='/static')
        
        CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
        
        # Register blueprints
        print("Registering blueprints...")
        app.register_blueprint(admin_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(static_bp)
        
        # Additional static file route as a fallback
        @app.route('/static/<path:filename>')
        def serve_static(filename):
            """Serve static files from the images directory"""
            logger.info(f"Attempting to serve static file: {filename}")
            try:
                return send_from_directory(
                    os.path.join('..', 'frontend', 'public', 'images'), 
                    filename
                )
            except Exception as e:
                logger.error(f"Error serving static file {filename}: {e}")
                return f"File not found: {filename}", 404
        
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
        save_placeholder_image()
        
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