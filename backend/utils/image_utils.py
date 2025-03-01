import os
import base64
import logging
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
    
    # Remove any "images/" prefix
    if path.startswith('images/'):
        path = path[7:]  # Remove "images/" prefix
        
    # Get just the filename without any path
    return os.path.basename(path)

def image_exists(filename):
    """Check if an image exists in the images directory"""
    if filename in IMAGE_EXISTENCE_CACHE:
        return IMAGE_EXISTENCE_CACHE[filename]
        
    # Check direct match
    full_path = os.path.join(IMAGES_DIR, filename)
    exists = os.path.exists(full_path)
    
    if not exists:
        # Try case-insensitive matching
        try:
            for f in os.listdir(IMAGES_DIR):
                if f.lower() == filename.lower():
                    exists = True
                    break
        except Exception:
            pass
    
    # Cache the result
    IMAGE_EXISTENCE_CACHE[filename] = exists
    return exists

def clear_image_caches():
    """Clear the image existence caches"""
    IMAGE_EXISTENCE_CACHE.clear()
    MISSING_IMAGE_CACHE.clear()

def generate_placeholder_image(color='#FF9999', size=(100, 100)):
    """Generate a base64 data URL for a placeholder image"""
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', size, color=color)
        draw = ImageDraw.Draw(img)
        
        # Draw a border
        border_color = '#CC0000'
        draw.rectangle([(0, 0), (size[0]-1, size[1]-1)], outline=border_color, width=4)
        
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
        return None

def save_placeholder_image(output_path='placeholder.png'):
    """Save a placeholder image file"""
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (200, 120), color='#FF9999')
        draw = ImageDraw.Draw(img)
        
        # Draw a border
        border_color = '#CC0000'
        draw.rectangle([(0, 0), (199, 119)], outline=border_color, width=4)
        
        # Add text
        draw.text((100, 60), "No Image", fill="#FFFFFF")
        
        # Save the image
        img.save(output_path)
        logger.info(f"Generated placeholder image at {output_path}")
        return True
    except ImportError:
        logger.warning("PIL not installed - cannot generate placeholder image")
        return False
    except Exception as e:
        logger.error(f"Error generating placeholder: {e}")
        return False