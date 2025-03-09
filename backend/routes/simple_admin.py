from flask import Blueprint, render_template, jsonify, request
import os
import logging
import traceback
from database import get_db_connection
from config import IMAGES_DIR

logger = logging.getLogger('image-similarity')
simple_admin_bp = Blueprint('simple_admin', __name__)

@simple_admin_bp.route('/simple-admin')
def simple_admin():
    """Render the simple admin page"""
    return render_template('simple_admin.html')

@simple_admin_bp.route('/simple-admin/reset-db', methods=['POST'])
def simple_reset_db():
    """Reset and repopulate the database from the images directory"""
    try:
        if not os.path.exists(IMAGES_DIR):
            return jsonify({
                "status": "error",
                "message": f"Images directory not found: {IMAGES_DIR}"
            }), 404
            
        # Get database connection
        db = get_db_connection()
        
        # Get populate_graph function
        try:
            from graph import populate_graph
        except ImportError:
            logger.error("Could not import populate_graph function")
            return jsonify({
                "status": "error",
                "message": "Could not import populate_graph function"
            }), 500
            
        # Clear the database first
        logger.info("Clearing database before repopulation")
        db.clear_database()
        
        # Populate the graph
        logger.info(f"Populating graph from {IMAGES_DIR}")
        success = populate_graph(IMAGES_DIR, similarity_threshold=0.7, generate_descriptions=True)
        
        if success:
            # Count images after populating
            image_count = db.count_images()
            
            return jsonify({
                "status": "success",
                "message": f"Database reset and populated with {image_count} images"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to populate database"
            }), 500
            
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc()
        }), 500

@simple_admin_bp.route('/simple-admin/fix-db', methods=['POST'])
def simple_fix_db():
    """Fix database by removing missing image nodes"""
    try:
        # Get database connection
        db = get_db_connection()
        
        # Get all image paths
        all_images = db.get_all_images()
        
        if not all_images:
            return jsonify({
                "status": "info",
                "message": "No images found in database"
            })
        
        # Check which images exist
        from utils.image_utils import normalize_image_path, image_exists
        
        missing_images = []
        for path in all_images:
            filename = normalize_image_path(path)
            if not image_exists(filename, force_check=True):
                missing_images.append(path)
        
        # Remove missing images
        if missing_images:
            removed_count = db.remove_images(missing_images)
            
            return jsonify({
                "status": "success",
                "message": f"Removed {removed_count} missing images from database",
                "total_removed": removed_count
            })
        else:
            return jsonify({
                "status": "success",
                "message": "No missing images found in database"
            })
            
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc()
        }), 500

@simple_admin_bp.route('/simple-admin/db-status', methods=['GET'])
def simple_db_status():
    """Get a simple database status"""
    try:
        # Get database connection
        db = get_db_connection()
        
        # Check connection
        try:
            db.driver.verify_connectivity()
            connection_status = "connected"
        except Exception as e:
            connection_status = f"error: {str(e)}"
            return jsonify({
                "status": "error",
                "connection": connection_status,
                "message": str(e)
            }), 500
        
        # Get image count
        try:
            image_count = db.count_images()
        except Exception:
            image_count = "unknown"
        
        # Get sample images
        try:
            sample_images = db.get_sample_images(limit=5)
        except Exception:
            sample_images = []
        
        return jsonify({
            "status": "success",
            "connection": connection_status,
            "image_count": image_count,
            "sample_images": sample_images
        })
            
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500