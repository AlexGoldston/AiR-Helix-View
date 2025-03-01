import logging
import threading
import time
from collections import deque
from config import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT, LOG_MAX_ENTRIES

# Create in-memory log storage
class MemoryLogHandler(logging.Handler):
    def __init__(self, max_entries=LOG_MAX_ENTRIES):
        super().__init__()
        self.log_entries = deque(maxlen=max_entries)
        self.lock = threading.Lock()
        
    def emit(self, record):
        with self.lock:
            self.log_entries.append({
                'timestamp': time.strftime(LOG_DATE_FORMAT, time.localtime(record.created)),
                'level': record.levelname,
                'message': self.format(record)
            })
    
    def get_logs(self, limit=100, level=None):
        with self.lock:
            entries = list(self.log_entries)
            if level:
                entries = [entry for entry in entries if entry['level'] == level]
            return entries[-limit:] if limit < len(entries) else entries
    
    def clear(self):
        with self.lock:
            self.log_entries.clear()

# Global memory handler instance
memory_handler = None

def setup_logging():
    """Configure logging and return the main logger"""
    global memory_handler
    
    # Configure basic logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    
    # Create a logger
    logger = logging.getLogger('image-similarity')
    
    # Create memory handler if not already created
    if memory_handler is None:
        memory_handler = MemoryLogHandler()
        memory_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(memory_handler)
    
    # Filter out excessive 404 logs from Werkzeug
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.ERROR)  # Only show errors, not info
    
    return logger

def get_memory_handler():
    """Get the memory log handler"""
    global memory_handler
    if memory_handler is None:
        setup_logging()
    return memory_handler