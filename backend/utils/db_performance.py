# backend/utils/db_performance.py
import time
import threading
import logging
from functools import wraps

logger = logging.getLogger('image-similarity')

# Global metrics
query_metrics = {
    'total_queries': 0,
    'total_time': 0,
    'avg_time': 0,
    'max_time': 0,
    'min_time': float('inf'),
    'query_types': {}
}

# Lock for thread safety
metrics_lock = threading.Lock()

def track_query_performance(query_type='default'):
    """
    Decorator to track Neo4j query performance.
    
    Args:
        query_type: Category/type of query for grouping metrics
    
    Usage:
        @track_query_performance("get_neighbors")
        def get_neighbors(self, image_path, threshold, limit):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_time = time.time() - start_time
                
                # Update metrics
                with metrics_lock:
                    # Update global metrics
                    query_metrics['total_queries'] += 1
                    query_metrics['total_time'] += elapsed_time
                    query_metrics['avg_time'] = query_metrics['total_time'] / query_metrics['total_queries']
                    query_metrics['max_time'] = max(query_metrics['max_time'], elapsed_time)
                    query_metrics['min_time'] = min(query_metrics['min_time'], elapsed_time)
                    
                    # Update per-query type metrics
                    if query_type not in query_metrics['query_types']:
                        query_metrics['query_types'][query_type] = {
                            'count': 0,
                            'total_time': 0,
                            'avg_time': 0,
                            'max_time': 0,
                            'min_time': float('inf')
                        }
                    
                    type_metrics = query_metrics['query_types'][query_type]
                    type_metrics['count'] += 1
                    type_metrics['total_time'] += elapsed_time
                    type_metrics['avg_time'] = type_metrics['total_time'] / type_metrics['count']
                    type_metrics['max_time'] = max(type_metrics['max_time'], elapsed_time)
                    type_metrics['min_time'] = min(type_metrics['min_time'], elapsed_time)
                
                # Log query performance
                logger.debug(f"Neo4j query ({query_type}) completed in {elapsed_time:.4f} seconds")
                
                # Log detailed metrics periodically (every 50 queries)
                if query_metrics['total_queries'] % 50 == 0:
                    log_performance_metrics()
        
        return wrapper
    return decorator

def log_performance_metrics():
    """Log current performance metrics"""
    with metrics_lock:
        logger.info(f"Neo4j Performance Metrics:")
        logger.info(f"  Total queries: {query_metrics['total_queries']}")
        logger.info(f"  Average time: {query_metrics['avg_time']:.4f} seconds")
        logger.info(f"  Min time: {query_metrics['min_time']:.4f} seconds")
        logger.info(f"  Max time: {query_metrics['max_time']:.4f} seconds")
        
        # Log by query type
        for query_type, metrics in query_metrics['query_types'].items():
            logger.info(f"  {query_type} queries:")
            logger.info(f"    Count: {metrics['count']}")
            logger.info(f"    Average time: {metrics['avg_time']:.4f} seconds")

def get_performance_metrics():
    """Get a copy of the current performance metrics"""
    with metrics_lock:
        return dict(query_metrics)

def reset_performance_metrics():
    """Reset all performance metrics"""
    with metrics_lock:
        query_metrics['total_queries'] = 0
        query_metrics['total_time'] = 0
        query_metrics['avg_time'] = 0
        query_metrics['max_time'] = 0
        query_metrics['min_time'] = float('inf')
        query_metrics['query_types'] = {}