import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_MAX_ENTRIES = 1000

# Explicitly set the images directory
IMAGES_DIR = r'C:\Users\alexa\dev\AiR-Helix-View\frontend\public\images'

# Verify the directory exists
if not os.path.exists(IMAGES_DIR):
    print(f"WARNING: Images directory does not exist: {IMAGES_DIR}")
    # Create the directory if it doesn't exist
    try:
        os.makedirs(IMAGES_DIR, exist_ok=True)
    except Exception as e:
        print(f"Failed to create images directory: {e}")

# Image types for searching
IMAGE_EXTENSIONS = ['*.jpg', '*.jpeg', '*.png', '*.gif']

# Default similarity threshold
DEFAULT_SIMILARITY_THRESHOLD = 0.5
DEFAULT_NEIGHBOR_LIMIT = 10