import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Neo4j driver configuration
NEO4J_CONNECTION_TIMEOUT = 5  # seconds
NEO4J_MAX_CONNECTION_LIFETIME = 3600  # seconds
NEO4J_MAX_CONNECTION_POOL_SIZE = 50
NEO4J_CONNECTION_ACQUISITION_TIMEOUT = 60  # seconds

# Rust extension configuration
NEO4J_RUST_EXT_DEBUG = False  # Set to True to enable debug logs
NEO4J_RUST_PERFORMANCE_MONITORING = True  # Track query performance

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_MAX_ENTRIES = 1000

# Explicitly set the images directory
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'public', 'images')

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

