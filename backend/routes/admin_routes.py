from flask import Blueprint, render_template, jsonify, request
import os
import glob
import logging
import traceback
import time
import threading
from database import get_db_connection
from utils.log_utils import get_memory_handler
from utils.image_utils import clear_image_caches, normalize_image_path, image_exists
from config import IMAGES_DIR, IMAGE_EXTENSIONS


logger = logging.getLogger('image-similarity')
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
def admin_dashboard():
    """Render the admin dashboard"""
    return render_template('admin.html')

@admin_bp.route('/admin/logs')
def view_logs():
    """View application logs"""
    level = request.args.get('level', None)
    limit = int(request.args.get('limit', 100))
    format_type = request.args.get('format', 'html')
    
    memory_handler = get_memory_handler()
    logs = memory_handler.get_logs(limit=limit, level=level)
    
    if format_type == 'json':
        return jsonify(logs)
        
    # If HTML format, render logs in a simple table
    logs_html = ""
    for log in logs:
        level_class = ""
        if log['level'] == 'ERROR':
            level_class = "color: red;"
        elif log['level'] == 'WARNING':
            level_class = "color: orange;"
        elif log['level'] == 'INFO':
            level_class = "color: green;"
            
        logs_html += f"<tr><td>{log['timestamp']}</td><td style='{level_class}'>{log['level']}</td><td>{log['message']}</td></tr>"
    
    return render_template('logs.html', logs_html=logs_html)

@admin_bp.route('/admin/logs/clear', methods=['POST'])
def clear_logs():
    """Clear application logs"""
    memory_handler = get_memory_handler()
    memory_handler.clear()
    return jsonify({"status": "ok"})

@admin_bp.route('/admin/reset-db', methods=['POST'])
def reset_db():
    """Reset and repopulate the database from the images directory"""
    try:
        if not os.path.exists(IMAGES_DIR):
            return jsonify({
                "error": f"Images directory not found: {IMAGES_DIR}"
            }), 404
            
        # Count images before populating
        image_files = []
        for ext in IMAGE_EXTENSIONS:
            image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
        
        if not image_files:
            return jsonify({
                "error": f"No images found in directory: {IMAGES_DIR}"
            }), 404
            
        # Get database connection
        db = get_db_connection()
        
        # Get populate_graph function
        try:
            from graph import populate_graph
        except ImportError:
            logger.error("Could not import populate_graph function")
            return jsonify({
                "error": "Could not import populate_graph function"
            }), 500
            
        # Clear the database first
        logger.info("Clearing database before repopulation")
        db.clear_database()
        
        # Populate the graph
        logger.info(f"Populating graph from {IMAGES_DIR} with {len(image_files)} images")
        populate_graph(IMAGES_DIR)
        
        # Clear image existence cache after repopulating
        clear_image_caches()
        
        return jsonify({
            "status": "OK",
            "message": f"Database reset and populated with {len(image_files)} images"
        })
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500

@admin_bp.route('/admin/fix-db', methods=['POST'])
def fix_db():
    """Remove nodes for images that don't exist in the filesystem"""
    try:
        # Get database connection
        db = get_db_connection()
        
        # Get all image nodes
        image_nodes = db.get_all_images()
        
        # Check which ones exist in the filesystem
        missing_nodes = []
        for node_path in image_nodes:
            filename = normalize_image_path(node_path)
            if not image_exists(filename):
                missing_nodes.append(node_path)
        
        # Remove missing nodes
        if missing_nodes:
            removed_count = db.remove_images(missing_nodes)
            
            # Clear the cache for missing images
            clear_image_caches()
            
            # Log info
            logger.info(f"Removed {removed_count} nodes for missing images from database")
            
            if removed_count > 20:
                # If many nodes removed, just report the count
                return jsonify({
                    "status": "OK",
                    "message": f"Removed {removed_count} nodes for missing images",
                    "removed_count": removed_count
                })
            else:
                # If just a few, list them
                return jsonify({
                    "status": "OK",
                    "message": f"Removed {removed_count} nodes for missing images",
                    "removed_images": missing_nodes
                })
        else:
            return jsonify({
                "status": "OK",
                "message": "No missing image nodes found"
            })
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500

@admin_bp.route('/debug/images')
def list_images():
    """List basic info about available images in the configured directory"""
    try:
        if not os.path.exists(IMAGES_DIR):
            return jsonify({
                "error": f"Images directory not found: {IMAGES_DIR}",
                "cwd": os.getcwd()
            }), 404
        
        # Count images by extension without loading all paths
        count_by_ext = {}
        total_count = 0
        
        for ext in IMAGE_EXTENSIONS:
            ext_name = ext.replace('*.', '')
            if os.name == 'nt':  # Windows
                pattern = os.path.join(IMAGES_DIR, ext)
                count = len(glob.glob(pattern))
            else:  # Linux, macOS, etc.
                pattern = os.path.join(IMAGES_DIR, ext)
                count_lower = len(glob.glob(pattern))
                pattern_upper = os.path.join(IMAGES_DIR, ext.upper())
                count_upper = len(glob.glob(pattern_upper))
                count = count_lower + count_upper
            
            count_by_ext[ext_name] = count
            total_count += count
        
        # Get a small sample of image files for display
        sample_images = []
        sample_limit = 5  # Reduced from all images to just 5 for speed
        
        for ext in IMAGE_EXTENSIONS:
            if os.name == 'nt':  # Windows
                pattern = os.path.join(IMAGES_DIR, ext)
                files = glob.glob(pattern)[:sample_limit]
                sample_images.extend([os.path.basename(f) for f in files])
            else:  # Linux, macOS, etc.
                pattern = os.path.join(IMAGES_DIR, ext)
                files = glob.glob(pattern)[:sample_limit]
                sample_images.extend([os.path.basename(f) for f in files])
                
                pattern_upper = os.path.join(IMAGES_DIR, ext.upper())
                files = glob.glob(pattern_upper)[:sample_limit]
                sample_images.extend([os.path.basename(f) for f in files])
            
            if len(sample_images) >= sample_limit:
                break
        
        return jsonify({
            "images_dir": IMAGES_DIR,
            "image_count": total_count,
            "count_by_extension": count_by_ext,
            "sample_images": sorted(sample_images)[:sample_limit]  # Sort for consistent output
        })
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        return jsonify({
            "error": str(e)
        }), 500

@admin_bp.route('/debug/sync')
def debug_sync():
    """Compare database images with filesystem images"""
    try:
        # Set default result for timeout
        result = {"sync_status": "ERROR", "error": "Timeout"}
        
        def check_sync():
            nonlocal result
            try:
                # Get database connection
                db = get_db_connection()
                
                # Fast-check if database is connected
                try:
                    db.driver.verify_connectivity()
                except Exception as e:
                    logger.error(f"Database connection error: {e}")
                    result = {
                        "error": f"Database connection error: {e}",
                        "sync_status": "ERROR"
                    }
                    return
                
                # Make sure images directory exists
                if not os.path.exists(IMAGES_DIR):
                    logger.error(f"Images directory not found: {IMAGES_DIR}")
                    result = {
                        "error": f"Images directory not found: {IMAGES_DIR}",
                        "sync_status": "ERROR"
                    }
                    return
                
                # Check image count in database, but don't get all paths
                try:
                    db_image_count = db.count_images()
                    logger.info(f"Retrieved database image count: {db_image_count}")
                except Exception as e:
                    logger.error(f"Error getting database image count: {e}")
                    result = {
                        "error": f"Error getting database image count: {e}",
                        "sync_status": "ERROR"
                    }
                    return
                    
                # Get images from filesystem - just count them without loading paths
                try:
                    fs_image_count = 0
                    for ext in IMAGE_EXTENSIONS:
                        if os.name == 'nt':  # Windows
                            pattern = os.path.join(IMAGES_DIR, ext)
                            fs_image_count += len(glob.glob(pattern))
                        else:  # Linux, macOS, etc.
                            pattern = os.path.join(IMAGES_DIR, ext)
                            fs_image_count += len(glob.glob(pattern))
                            pattern_upper = os.path.join(IMAGES_DIR, ext.upper())
                            fs_image_count += len(glob.glob(pattern_upper))
                    
                    logger.info(f"Found {fs_image_count} images in filesystem")
                    
                    # Simple sync status based on counts alone - faster response
                    sync_needed = db_image_count != fs_image_count
                    logger.info(f"Sync result: db_count={db_image_count}, fs_count={fs_image_count}")
                    
                    result = {
                        "db_image_count": db_image_count,
                        "fs_image_count": fs_image_count,
                        "sync_needed": sync_needed,
                        "sync_status": "OK"
                    }
                    
                except Exception as e:
                    logger.error(f"Error counting filesystem images: {e}")
                    result = {
                        "error": f"Error counting filesystem images: {e}",
                        "sync_status": "ERROR"
                    }
                    return
                
            except Exception as e:
                logger.error(f"Error checking sync: {e}")
                result = {
                    "error": str(e),
                    "sync_status": "ERROR"
                }
        
        # Run with a short timeout for UI responsiveness
        thread = threading.Thread(target=check_sync)
        thread.daemon = True
        thread.start()
        thread.join(timeout=2)  # 2-second timeout
        
        if thread.is_alive():
            logger.error("Sync operation timed out")
            return jsonify({
                "sync_status": "ERROR",
                "error": "Sync operation timed out after 2 seconds"
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in debug_sync: {e}")
        return jsonify({
            "error": str(e),
            "sync_status": "ERROR"
        }), 500

@admin_bp.route('/debug/ping')
def debug_ping():
    """Simple ping endpoint for testing"""
    return jsonify({"status": "OK", "message": "Ping successful", "timestamp": time.time()})

@admin_bp.route('/debug/db')
def debug_db():
    """Check Neo4j database connection and contents"""
    try:
        # Create a timeout mechanism
        result = {"connection": "ERROR", "error": "Timeout"}
        
        def check_db():
            nonlocal result
            try:
                # Get database connection
                db = get_db_connection()
                
                # Only check connectivity first - this is the most important
                try:
                    logger.info("Checking database connection...")
                    db.driver.verify_connectivity()
                    logger.info("Database connection successful")
                    
                    # Successfully connected - set a minimal result
                    result = {
                        "connection": "OK",
                        "neo4j_uri": os.getenv("NEO4J_URI", "Not set"),
                        "timestamp": time.time()
                    }
                    
                    # Try to get image count, but don't block on it
                    try:
                        image_count = db.count_images()
                        logger.info(f"Database contains {image_count} images")
                        result["image_count"] = image_count
                    except Exception as e:
                        logger.error(f"Error counting images: {e}")
                        # Don't fail the entire check if this fails
                        result["image_count"] = "ERROR"
                    
                except Exception as e:
                    logger.error(f"Database connection error: {e}")
                    result = {
                        "connection": "ERROR",
                        "error": str(e),
                        "neo4j_uri": os.getenv("NEO4J_URI", "Not set")
                    }
            except Exception as e:
                logger.error(f"Unexpected error in debug_db: {e}")
                result = {
                    "connection": "ERROR",
                    "error": str(e)
                }
        
        # Run with a slightly longer timeout
        thread = threading.Thread(target=check_db)
        thread.daemon = True
        thread.start()
        thread.join(timeout=10)  # 10-second timeout
        
        if thread.is_alive():
            logger.error("Database check timed out")
            return jsonify({
                "connection": "ERROR",
                "error": "Database check timed out after 10 seconds. The database might be slow to respond.",
                "neo4j_uri": os.getenv("NEO4J_URI", "Not set"),
                "status_message": "Database is slow or unresponsive - check Neo4j server status"
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in debug_db: {e}")
        return jsonify({
            "connection": "ERROR",
            "error": str(e)
        })