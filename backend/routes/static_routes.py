from flask import Blueprint, send_from_directory, redirect, url_for
import os
import logging
from utils.image_utils import normalize_image_path, image_exists, save_placeholder_image
from utils.image_utils import MISSING_IMAGE_CACHE
from config import IMAGES_DIR

logger = logging.getLogger('image-similarity')
static_bp = Blueprint('static', __name__)

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
    # Clean up filename and remove any path components
    filename = normalize_image_path(filename)
    
    # Log the request at debug level
    logger.debug(f"Image request for: {filename}")
    logger.debug(f"Looking in directory: {IMAGES_DIR}")
    
    # Security check to prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        logger.warning(f"Invalid file path requested: {filename}")
        return "Invalid file path", 400
    
    # Skip cache check and logging for images we know don't exist
    if filename in MISSING_IMAGE_CACHE:
        logger.debug(f"Serving placeholder for known missing image: {filename}")
        return redirect('/placeholder', code=302)
    
    # Look for the file with case-insensitive matching
    real_filename = None
    full_path = os.path.join(IMAGES_DIR, filename)
    
    # Check if file exists directly
    if os.path.exists(full_path) and os.path.isfile(full_path):
        real_filename = filename
        logger.debug(f"Found exact match: {filename}")
    else:
        # Try to find the file with case-insensitive matching
        try:
            for f in os.listdir(IMAGES_DIR):
                if f.lower() == filename.lower():
                    real_filename = f
                    logger.debug(f"Found case-insensitive match: {f}")
                    break
        except Exception as e:
            logger.error(f"Error listing directory {IMAGES_DIR}: {e}")
    
    if not real_filename:
        # Only log the first occurrence of each missing image
        if filename not in MISSING_IMAGE_CACHE:
            logger.warning(f"Image not found: {filename} in {IMAGES_DIR}")
            logger.warning(f"Absolute path would be: {os.path.abspath(full_path)}")
            # Add to cache to avoid repeat logging
            MISSING_IMAGE_CACHE.add(filename)
        
        # Redirect to placeholder
        return redirect('/placeholder', code=302)
    
    # Log successful requests at debug level
    logger.debug(f"Serving image: {real_filename} from {IMAGES_DIR}")
    
    # Set cache control to prevent caching issues
    try:
        response = send_from_directory(IMAGES_DIR, real_filename)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error serving {real_filename} from {IMAGES_DIR}: {e}")
        return redirect('/placeholder', code=302)