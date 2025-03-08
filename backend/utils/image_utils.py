import os
import base64
import logging
import glob
import traceback
from config import IMAGES_DIR

logger = logging.getLogger('image-similarity')

# Cache for image existence checks
IMAGE_EXISTENCE_CACHE = {}
# Cache for missing image requests
MISSING_IMAGE_CACHE = set()

def normalize_image_path(path):
    """Extract just the filename from any path format"""
    if path is None:
        return None
    
    # Remove any query parameters (like ?v=timestamp)
    path = path.split('?')[0]
    
    # Remove any "images/" prefix
    if path.startswith('images/'):
        path = path[7:]  # Remove "images/" prefix
        
    # Get just the filename without any path
    return os.path.basename(path)

def image_exists(filename, force_check=False):
    """Check if an image exists in the images directory"""
    # Normalize filename
    filename = normalize_image_path(filename)
    
    # Check cache if not forcing a fresh check
    if not force_check and filename in IMAGE_EXISTENCE_CACHE:
        return IMAGE_EXISTENCE_CACHE[filename]
    
    # Full path construction
    full_path = os.path.join(IMAGES_DIR, filename)
    
    # Direct check with detailed logging
    logger.debug(f"Checking image existence: {filename}")
    logger.debug(f"Full path: {full_path}")
    
    # Try case-sensitive first
    exists = os.path.exists(full_path) and os.path.isfile(full_path)
    
    if exists:
        logger.debug(f"Image exists at path: {full_path}")
    else:
        logger.debug(f"Image not found at direct path, trying case-insensitive match")
        
        # If not found, try case-insensitive
        try:
            # Check if directory exists first
            if os.path.exists(IMAGES_DIR):
                directory_files = os.listdir(IMAGES_DIR)
                for f in directory_files:
                    if f.lower() == filename.lower():
                        exists = True
                        logger.debug(f"Found case-insensitive match: {f}")
                        break
            else:
                logger.warning(f"Images directory doesn't exist: {IMAGES_DIR}")
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            logger.error(traceback.format_exc())
    
    # Cache the result
    IMAGE_EXISTENCE_CACHE[filename] = exists
    
    if not exists:
        logger.debug(f"Image {filename} not found in {IMAGES_DIR}")
    
    return exists

def list_all_images():
    """Get a list of all images in the images directory"""
    if not os.path.exists(IMAGES_DIR):
        logger.warning(f"Images directory doesn't exist: {IMAGES_DIR}")
        return []
    
    all_images = []
    try:
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            # On Windows, we only need to do this once since the filesystem is case-insensitive
            if os.name == 'nt':  # Windows
                all_images.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
            else:  # Linux, macOS, etc.
                all_images.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
                all_images.extend(glob.glob(os.path.join(IMAGES_DIR, ext.upper())))
        
        # Convert to just filenames
        all_images = [os.path.basename(f) for f in all_images]
        
        # Remove duplicates
        all_images = list(set(all_images))
        
        logger.info(f"Found {len(all_images)} images in {IMAGES_DIR}")
        return all_images
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        logger.error(traceback.format_exc())
        return []

def clear_image_caches():
    """Clear the image existence caches"""
    logger.info("Clearing image existence caches")
    IMAGE_EXISTENCE_CACHE.clear()
    MISSING_IMAGE_CACHE.clear()

def generate_placeholder_image(color='#FF9999', size=(100, 100)):
    """Generate a base64 data URL for a placeholder image"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', size, color=color)
        draw = ImageDraw.Draw(img)
        
        # Draw a border
        border_color = '#CC0000'
        draw.rectangle([(0, 0), (size[0]-1, size[1]-1)], outline=border_color, width=4)
        
        # Add text (optional)
        try:
            draw.text((size[0]//2, size[1]//2), "No Image", fill="#FFFFFF")
        except Exception:
            # Text rendering failed, continue anyway
            pass
        
        # Convert to base64
        import io
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"
    except ImportError:
        logger.warning("PIL not installed - cannot generate placeholder image")
        return None
    except Exception as e:
        logger.error(f"Error generating placeholder: {e}")
        logger.error(traceback.format_exc())
        return None

def save_placeholder_image(output_path='placeholder.png'):
    """Save a placeholder image file"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (200, 120), color='#FF9999')
        draw = ImageDraw.Draw(img)
        
        # Draw a border
        border_color = '#CC0000'
        draw.rectangle([(0, 0), (199, 119)], outline=border_color, width=4)
        
        # Add text
        try:
            draw.text((100, 60), "No Image", fill="#FFFFFF")
        except Exception as e:
            logger.warning(f"Failed to add text to placeholder: {e}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Save the image
        img.save(output_path)
        logger.info(f"Generated placeholder image at {output_path}")
        return True
    except ImportError:
        logger.warning("PIL not installed - cannot generate placeholder image")
        return False
    except Exception as e:
        logger.error(f"Error generating placeholder: {e}")
        logger.error(traceback.format_exc())
        return False

def verify_image_directory():
    """Verify that the images directory exists and is accessible"""
    try:
        if not os.path.exists(IMAGES_DIR):
            logger.warning(f"Images directory doesn't exist: {IMAGES_DIR}")
            os.makedirs(IMAGES_DIR, exist_ok=True)
            logger.info(f"Created images directory: {IMAGES_DIR}")
        
        # Test file creation
        test_path = os.path.join(IMAGES_DIR, '.test_file')
        try:
            with open(test_path, 'w') as f:
                f.write('test')
            os.remove(test_path)
            logger.info(f"Directory {IMAGES_DIR} is writable")
        except Exception as e:
            logger.warning(f"Directory {IMAGES_DIR} is not writable: {e}")
        
        return {
            "exists": os.path.exists(IMAGES_DIR),
            "is_dir": os.path.isdir(IMAGES_DIR),
            "is_readable": os.access(IMAGES_DIR, os.R_OK),
            "is_writable": os.access(IMAGES_DIR, os.W_OK),
            "images_count": len(list_all_images()),
            "path": os.path.abspath(IMAGES_DIR)
        }
    except Exception as e:
        logger.error(f"Error verifying image directory: {e}")
        logger.error(traceback.format_exc())
        return {
            "exists": False,
            "error": str(e)
        }

def image_exists(filename, force_check=False):
    # Normalize filename
    filename = normalize_image_path(filename)
    
    # Check cache if not forcing a fresh check
    if not force_check and filename in IMAGE_EXISTENCE_CACHE:
        return IMAGE_EXISTENCE_CACHE[filename]
    
    # Full path construction
    full_path = os.path.join(IMAGES_DIR, filename)
    
    # Direct check with detailed logging
    logger.debug(f"Checking image existence: {filename}")
    logger.debug(f"Full path: {full_path}")
    
    # Check if file exists
    exists = os.path.exists(full_path) and os.path.isfile(full_path)
    
    # Cache the result
    IMAGE_EXISTENCE_CACHE[filename] = exists
    
    return exists