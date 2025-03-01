from flask import Blueprint, send_from_directory, redirect, url_for, request
import os
import logging
import traceback
from utils.image_utils import normalize_image_path, image_exists, save_placeholder_image
from utils.image_utils import MISSING_IMAGE_CACHE
from config import IMAGES_DIR

logger = logging.getLogger('image-similarity')
static_bp = Blueprint('static', __name__)

# Use the exact frontend/public/images path
FRONTEND_IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'public', 'images'))

@static_bp.route('/placeholder')
def placeholder_image():
    """Return a placeholder image for missing images"""
    try:
        # Check if we have a placeholder file already
        placeholder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'placeholder.png')
        if not os.path.exists(placeholder_path):
            # Try to generate one
            save_placeholder_image(placeholder_path)
        
        if os.path.exists(placeholder_path):
            # Return the placeholder file
            return send_from_directory(
                os.path.dirname(placeholder_path),
                os.path.basename(placeholder_path),
                mimetype='image/png'
            )
    except Exception as e:
        logger.error(f"Error serving placeholder: {e}")
    
    # Final fallback
    response = static_bp.response_class(
        response=b"Placeholder",
        status=200,
        mimetype='text/plain'
    )
    return response

@static_bp.route('/static/<path:filename>')
def serve_image(filename):
    """Serve static image files"""
    # Log the entire request for debugging
    logger.info("IMAGE REQUEST DETAILS:")
    logger.info(f"Full request URL: {request.url}")
    logger.info(f"Request method: {request.method}")
    
    # Clean up filename and remove any path components or query parameters
    original_filename = filename
    filename = normalize_image_path(filename)
    
    logger.info(f"Original filename: {original_filename}")
    logger.info(f"Normalized filename: {filename}")
    logger.info(f"Frontend Images directory: {FRONTEND_IMAGES_DIR}")
    
    # Security check to prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        logger.warning(f"Invalid file path requested: {filename}")
        return "Invalid file path", 400
    
    # Skip cache check and logging for images we know don't exist
    if filename in MISSING_IMAGE_CACHE:
        logger.info(f"Serving placeholder for known missing image: {filename}")
        return redirect('/placeholder', code=302)
    
    # Look for the file with case-insensitive matching
    real_filename = None
    full_path = os.path.join(FRONTEND_IMAGES_DIR, filename)
    
    # Check if file exists directly
    if os.path.exists(full_path) and os.path.isfile(full_path):
        real_filename = filename
        logger.info(f"Found exact match: {filename}")
    else:
        # Try to find the file with case-insensitive matching
        try:
            directory_files = os.listdir(FRONTEND_IMAGES_DIR)
            for f in directory_files:
                if f.lower() == filename.lower():
                    real_filename = f
                    logger.info(f"Found case-insensitive match: {f}")
                    break
        except Exception as e:
            logger.error(f"Error searching directory {FRONTEND_IMAGES_DIR}: {e}")
    
    if not real_filename:
        # Log very detailed error information
        logger.error(f"IMAGE NOT FOUND: {filename}")
        logger.error(f"Full attempted path: {full_path}")
        logger.error(f"Absolute images directory: {os.path.abspath(FRONTEND_IMAGES_DIR)}")
        logger.error(f"Current working directory: {os.getcwd()}")
        
        # Try to list all files again with absolute paths
        try:
            logger.error("Absolute paths of files:")
            for root, dirs, files in os.walk(FRONTEND_IMAGES_DIR):
                for f in files:
                    logger.error(f" - {os.path.join(root, f)}")
        except Exception as list_error:
            logger.error(f"Could not list files: {list_error}")
        
        # Add to cache to avoid repeat logging
        MISSING_IMAGE_CACHE.add(filename)
        
        # Detailed error with traceback
        try:
            logger.error("Full traceback:", exc_info=True)
        except Exception:
            pass
        
        # Redirect to placeholder
        return redirect('/placeholder', code=302)
    
    # Log successful file serving details
    log_path = os.path.join(FRONTEND_IMAGES_DIR, real_filename)
    logger.info(f"Serving image: {real_filename}")
    logger.info(f"Full image path: {log_path}")
    logger.info(f"Image file exists: {os.path.exists(log_path)}")
    logger.info(f"Is file: {os.path.isfile(log_path)}")
    
    # Set cache control to prevent caching issues
    try:
        response = send_from_directory(FRONTEND_IMAGES_DIR, real_filename)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error serving {real_filename} from {FRONTEND_IMAGES_DIR}: {e}")
        # Log full traceback
        logger.error("Full traceback:", exc_info=True)
        return redirect('/placeholder', code=302)