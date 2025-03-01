from flask import Blueprint, render_template, jsonify, request
import os
import glob
import logging
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
        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500

@admin_bp.route('/debug/images')
def list_images():
    """List all available images in the configured directory"""
    if not os.path.exists(IMAGES_DIR):
        return jsonify({
            "error": f"Images directory not found: {IMAGES_DIR}",
            "cwd": os.getcwd()
        }), 404
    
    # List all image files
    image_files = []
    for ext in IMAGE_EXTENSIONS:
        # On Windows, we only need to do this once since the filesystem is case-insensitive
        if os.name == 'nt':  # Windows
            image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
        else:  # Linux, macOS, etc.
            image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
            image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext.upper())))
    
    # Format the results and remove duplicates
    images = list(set(os.path.basename(f) for f in image_files))
    
    return jsonify({
        "images_dir": IMAGES_DIR,
        "image_count": len(images),
        "images": sorted(images)  # Sort for consistent output
    })

@admin_bp.route('/debug/sync')
def debug_sync():
    """Compare database images with filesystem images"""
    try:
        # Get database connection
        db = get_db_connection()
        
        # Get images from database
        db_images = db.get_all_images()
        
        # Get images from filesystem
        fs_images = []
        # Use the same improved pattern as list_images to avoid duplicates
        for ext in IMAGE_EXTENSIONS:
            if os.name == 'nt':  # Windows
                fs_images.extend([os.path.basename(f) for f in glob.glob(os.path.join(IMAGES_DIR, ext))])
            else:  # Linux, macOS, etc.
                fs_images.extend([os.path.basename(f) for f in glob.glob(os.path.join(IMAGES_DIR, ext))])
                fs_images.extend([os.path.basename(f) for f in glob.glob(os.path.join(IMAGES_DIR, ext.upper()))])
        
        # Remove duplicates
        fs_images = list(set(fs_images))
        
        # Normalize all paths to just filenames
        db_images = [normalize_image_path(img) for img in db_images]
        
        # Find differences
        missing_in_fs = [img for img in db_images if img not in fs_images]
        missing_in_db = [img for img in fs_images if img not in db_images]
        
        return jsonify({
            "db_image_count": len(db_images),
            "fs_image_count": len(fs_images),
            "missing_in_filesystem": missing_in_fs,
            "missing_in_database": missing_in_db,
            "sync_needed": len(missing_in_fs) > 0 or len(missing_in_db) > 0
        })
    except Exception as e:
        logger.error(f"Error checking sync: {e}")
        return jsonify({
            "error": str(e)
        }), 500

@admin_bp.route('/debug/db')
def debug_db():
    """Check Neo4j database connection and contents"""
    try:
        # Get database connection
        db = get_db_connection()
        
        # Check connection
        db.driver.verify_connectivity()
        
        # Get image count
        image_count = db.count_images()
        
        # Get some sample images
        sample_images = db.get_sample_images(10)
        
        # Try to get specific image
        test_image = request.args.get('image', 'allianz_stadium_sydney01.jpg')
        image_node = db.find_image_by_path(test_image)
        
        # Also try with images/ prefix
        image_node_with_prefix = db.find_image_by_path(f"images/{test_image}")
        
        return jsonify({
            "connection": "OK",
            "image_count": image_count,
            "sample_images": sample_images,
            "test_image": test_image,
            "image_found": image_node is not None,
            "image_with_prefix_found": image_node_with_prefix is not None
        })
    except Exception as e:
        logger.error(f"Error checking database: {e}")
        return jsonify({
            "connection": "ERROR",
            "error": str(e)
        }), 500