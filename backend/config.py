import os
import glob
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "devpassword")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_MAX_ENTRIES = 1000

# Image directory configuration
POSSIBLE_IMAGE_DIRS = [
    r'C:\Users\alexa\dev\AiR-Helix-View\frontend\public\images',  # Absolute path for Windows
    os.path.join('..', 'frontend', 'public', 'images'),  # Relative path
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'public', 'images'),  # Another relative path
    'images',  # Fallback local directory
    os.path.join('frontend', 'public', 'images'),
    os.path.join(os.getcwd(), 'images'),
    os.path.join(os.getcwd(), '..', 'frontend', 'public', 'images')
]

# Find the first valid images directory
def get_images_dir():
    for path in POSSIBLE_IMAGE_DIRS:
        if os.path.exists(path):
            return os.path.abspath(path)
    
    # Create 'images' directory as fallback if none exists
    fallback_dir = os.path.join(os.getcwd(), 'images')
    try:
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir
    except Exception:
        return 'images'  # Last resort fallback

IMAGES_DIR = get_images_dir()

# Image types for searching
IMAGE_EXTENSIONS = ['*.jpg', '*.jpeg', '*.png', '*.gif']

# Default similarity threshold
DEFAULT_SIMILARITY_THRESHOLD = 0.7
DEFAULT_NEIGHBOR_LIMIT = 20