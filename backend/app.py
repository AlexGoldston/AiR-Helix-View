from flask import Flask
from flask_cors import CORS
import os
import glob
import logging
from routes.admin_routes import admin_bp
from routes.api_routes import api_bp
from routes.static_routes import static_bp
from utils.log_utils import setup_logging
from utils.template_utils import ensure_template_files
from utils.image_utils import save_placeholder_image
from config import IMAGES_DIR, IMAGE_EXTENSIONS

# Initialize logging
logger = setup_logging()

def create_app():
    """Create and configure the Flask application"""
    # Ensure template files exist
    ensure_template_files()
    
    # Create Flask app
    app = Flask(__name__, template_folder='templates')
    CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
    
    # Register blueprints
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(static_bp)
    
    # Basic error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {str(e)}")
        return {"error": "Internal server error"}, 500
    
    @app.route('/')
    def index():
        return "Image similarity API - Visit /admin for management"
    
    return app

if __name__ == '__main__':
    # Create a placeholder image at startup
    save_placeholder_image()
    
    # Check for image directory
    if os.path.exists(IMAGES_DIR):
        logger.info(f"Available images in {IMAGES_DIR}:")
        image_count = 0
        for ext in IMAGE_EXTENSIONS:
            for img in glob.glob(os.path.join(IMAGES_DIR, ext)):
                if image_count < 10:  # Only print the first 10 images
                    logger.info(f" - {os.path.basename(img)}")
                image_count += 1
        if image_count > 10:
            logger.info(f" ... and {image_count - 10} more images")
        logger.info(f"Total images found: {image_count}")
    else:
        logger.warning(f"WARNING: Image directory '{IMAGES_DIR}' not found")
    
    # Start the application
    app = create_app()
    logger.info("Starting Flask application...")
    app.run(debug=True, port=5001)