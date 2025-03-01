import logging
import threading
import time
import os
import sys
import platform
from collections import deque
from config import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT, LOG_MAX_ENTRIES, IMAGES_DIR, NEO4J_URI

# Create in-memory log storage
class MemoryLogHandler(logging.Handler):
    def __init__(self, max_entries=LOG_MAX_ENTRIES):
        super().__init__()
        self.log_entries = deque(maxlen=max_entries)
        self.lock = threading.Lock()
        
    def emit(self, record):
        with self.lock:
            try:
                # Try to format the entire log record
                log_entry = {
                    'timestamp': time.strftime(LOG_DATE_FORMAT, time.localtime(record.created)),
                    'level': record.levelname,
                    'message': self.format(record),
                    # Additional context if available
                    'module': record.module,
                    'filename': record.filename,
                    'lineno': record.lineno
                }
                self.log_entries.append(log_entry)
            except Exception as e:
                # Fallback logging in case of formatting issues
                print(f"Error in log emission: {e}")
                print(f"Original record: {record.__dict__}")
    
    def get_logs(self, limit=100, level=None):
        with self.lock:
            entries = list(self.log_entries)
            
            # Filter by log level if specified
            if level:
                entries = [entry for entry in entries if entry['level'] == level]
            
            # Sort entries by timestamp (most recent first)
            entries.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Return limited entries
            return entries[:limit]
    
    def clear(self):
        with self.lock:
            self.log_entries.clear()

# Global memory handler instance
memory_handler = None

def setup_logging():
    """Configure logging and return the main logger"""
    global memory_handler
    
    # Configure logging handlers
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(),  # Console output
            # Optional: File logging
            logging.FileHandler('app.log', encoding='utf-8')
        ]
    )
    
    # Create a logger
    logger = logging.getLogger('image-similarity')
    
    # Ensure memory handler is created only once
    if memory_handler is None:
        memory_handler = MemoryLogHandler()
        memory_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(memory_handler)
    
    # Configure Werkzeug logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.WARNING)  # Reduce noise
    
    # Add memory handler to other key loggers
    for log_name in ['neo4j', 'urllib3', 'flask']:
        sub_logger = logging.getLogger(log_name)
        sub_logger.addHandler(memory_handler)
    
    return logger

def get_memory_handler():
    """Get the memory log handler"""
    global memory_handler
    if memory_handler is None:
        setup_logging()
    return memory_handler

def log_startup_info():
    """Log system and application startup information"""
    logger = logging.getLogger('image-similarity')
    
    # Log system information
    logger.info("Application Startup")
    logger.info(f"Logging level: {LOG_LEVEL}")
    
    # Log environment details
    try:
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {platform.platform()}")
        logger.info(f"Current working directory: {os.getcwd()}")
    except Exception as e:
        logger.error(f"Error logging system info: {e}")
    
    # Optional: Log configuration details
    try:
        logger.info(f"Images directory: {IMAGES_DIR}")
        logger.info(f"Neo4j URI: {NEO4J_URI}")
        
        # List images in the directory
        if os.path.exists(IMAGES_DIR):
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
                import glob
                image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
                image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext.upper())))
            
            logger.info(f"Total images found: {len(image_files)}")
            if image_files:
                logger.info("Sample image paths:")
                for img in image_files[:5]:
                    logger.info(f" - {os.path.basename(img)}")
                if len(image_files) > 5:
                    logger.info(f" ... and {len(image_files) - 5} more")
        else:
            logger.warning(f"Images directory does not exist: {IMAGES_DIR}")
    except Exception as e:
        logger.error(f"Error logging configuration details: {e}")