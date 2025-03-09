from flask import Flask, send_from_directory
from flask_cors import CORS
import os
# import glob
import logging
import traceback
import sys
import threading
import time
import signal
import atexit
import argparse
# from concurrent.futures import ThreadPoolExecutor, TimeoutError

# Parse command line arguments
parser = argparse.ArgumentParser(description='Image Similarity Explorer Backend')
parser.add_argument('--skip-db-init', action='store_true', 
                    help='Skip database initialization on startup (faster startup)')
parser.add_argument('--debug', action='store_true',
                    help='Run in debug mode (more verbose logging)')
args = parser.parse_args()

# Configure Rust extension debugging based on debug flag
if args.debug:
    os.environ["NEO4J_RUST_EXT_DEBUG"] = "1"
else:
    os.environ["NEO4J_RUST_EXT_DEBUG"] = "0" 

print("Starting import of modules...")

print("Importing routes...")
from routes.admin_routes import admin_bp
from routes.api_routes import api_bp
from routes.static_routes import static_bp
from routes.simple_admin import simple_admin_bp

print("Importing utils...")
from utils.image_utils import save_placeholder_image, normalize_image_path
from config import IMAGES_DIR, IMAGE_EXTENSIONS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('app.log', encoding='utf-8')  # File output
    ]
)
logger = logging.getLogger('image-similarity')
logger.info("Basic logging initialized")

# Global references for shutdown
server = None
server_thread = None
shutdown_requested = False

def create_app():
    """Create and configure the Flask application"""
    try:
        print("Creating Flask app...")
        
        # Create Flask app
        app = Flask(__name__, 
                    template_folder='templates', 
                    static_folder=os.path.join('..', 'frontend', 'public', 'images'),
                    static_url_path='/static')
        
        CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
        
        # Register blueprints
        print("Registering blueprints...")
        app.register_blueprint(admin_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(static_bp)
        app.register_blueprint(simple_admin_bp)
        
        # Additional static file route as a fallback
        @app.route('/static/<path:filename>')
        def serve_static(filename):
            """Serve static files from the images directory"""
            logger.info(f"Attempting to serve static file: {filename}")
            try:
                return send_from_directory(
                    os.path.join('..', 'frontend', 'public', 'images'), 
                    filename
                )
            except Exception as e:
                logger.error(f"Error serving static file {filename}: {e}")
                return f"File not found: {filename}", 404
        
        # Detailed error handler
        @app.errorhandler(Exception)
        def handle_exception(e):
            # Log the full traceback
            logger.error(f"Unhandled exception: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": "Internal server error", "details": str(e)}, 500
        
        @app.route('/')
        def index():
            return "Image similarity API - Visit /admin for management"
        
        print("Flask app created successfully")
        return app
    
    except Exception as e:
        print(f"Failed to create app: {str(e)}")
        logger.error(f"Failed to create app: {str(e)}")
        traceback.print_exc()
        raise

def close_logging_handlers():
    """Close all logging handlers to release file handles"""
    print("Closing logging handlers...")
    
    # Close all handlers for our logger
    for handler in logger.handlers[:]:
        try:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)
        except Exception as e:
            print(f"Error closing logger handler: {e}")
    
    # Close root logger handlers too
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        try:
            handler.flush()
            handler.close()
            root_logger.removeHandler(handler)
        except Exception as e:
            print(f"Error closing root logger handler: {e}")
    
    # Close all loggers
    for name in logging.root.manager.loggerDict:
        log = logging.getLogger(name)
        for handler in log.handlers[:]:
            try:
                handler.flush()
                handler.close()
                log.removeHandler(handler)
            except Exception as e:
                print(f"Error closing handler for logger {name}: {e}")

def shutdown_server():
    """Properly shutdown the server and clean up resources"""
    global server, server_thread, shutdown_requested
    
    if shutdown_requested:
        return
    
    shutdown_requested = True
    print("Shutting down server...")
    
    # try to stop the server gracefully
    if server:
        try:
            server.shutdown()
            print("Server shutdown initiated")
        except Exception as e:
            print(f"Error during server shutdown: {e}")
    
    # Close all logging handlers
    close_logging_handlers()
    
    # Force exit after a brief delay if we're still running
    def force_exit():
        time.sleep(1)  # Give a second for shutdown to complete
        print("Forcing exit...")
        os._exit(0)  # Hard exit
    
    # Start force exit thread
    threading.Thread(target=force_exit, daemon=True).start()

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    print("\nCaught signal - shutting down...")
    shutdown_server()

def main():
    global server, server_thread
    
    try:
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register shutdown function with atexit
        atexit.register(shutdown_server)
        
        print("Starting main function...")
        logger.info("Starting main function")
        
        # Create a placeholder image at startup - this should be quick
        print("Creating placeholder image...")
        save_placeholder_image()

        # Modify database initialization behavior based on skip-db-init flag
        if args.skip_db_init:
            logger.info("Skipping database initialization at startup (--skip-db-init flag used)")
            # Import a modified version of get_db_connection so we don't trigger Neo4j connection
            from database import get_db_connection as original_get_db_conn
            
            # Override the database module's get_db_connection function with a lazy version
            import database
            
            # Original function is now wrapped to be lazy
            def lazy_get_db_connection():
                logger.info("Lazy database connection requested")
                return original_get_db_conn()
            
            # Replace the function with our lazy version
            database.get_db_connection = lazy_get_db_connection
            logger.info("Database initialization deferred until first use")
        else:
            logger.info("Initializing database connection at startup")
            # This will trigger the database connection initialization
            from database import get_db_connection
            logger.info("Database initialization complete")
        
        # Start the application
        print("Creating Flask application...")
        app = create_app()
        logger.info("Starting Flask application...")
        
        # Use threaded mode to help with potential blocking issues
        print("Starting Flask server...")
        from werkzeug.serving import make_server
        server = make_server('127.0.0.1', 5001, app)

        # Run in separate thread
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print('Flask server started - press ctrl+c to stop')
        if args.skip_db_init:
            print('Database initialization skipped - will connect on first database access')
        
        # Run until interrupted
        while server_thread.is_alive() and not shutdown_requested:
            time.sleep(1)  # Check every second
            
    except Exception as e:
        print(f"Critical error during app startup: {str(e)}")
        logger.error(f"Critical error during app startup: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    print("Script starting...")
    main()
    print("Script completed.")