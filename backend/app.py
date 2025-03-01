from flask import Flask, jsonify, request, send_from_directory, render_template_string, redirect
from flask_cors import CORS
from graph import Neo4jConnection, populate_graph
import os
import glob
import json
import base64
import logging
import time
from collections import deque
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Create a logger
logger = logging.getLogger('image-similarity')

# Create in-memory log storage
class MemoryLogHandler(logging.Handler):
    def __init__(self, max_entries=1000):
        super().__init__()
        self.log_entries = deque(maxlen=max_entries)
        self.lock = threading.Lock()
        
    def emit(self, record):
        with self.lock:
            self.log_entries.append({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created)),
                'level': record.levelname,
                'message': self.format(record)
            })
    
    def get_logs(self, limit=100, level=None):
        with self.lock:
            if level:
                return list(filter(lambda x: x['level'] == level, list(self.log_entries)))[-limit:]
            return list(self.log_entries)[-limit:]
    
    def clear(self):
        with self.lock:
            self.log_entries.clear()

# Create memory handler
memory_handler = MemoryLogHandler()
memory_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(memory_handler)

# Filter out excessive 404 logs from Werkzeug
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)  # Only show errors, not info

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})  # Allow all origins

# Configure the images directory paths to try
POSSIBLE_IMAGE_DIRS = [
    os.path.join('..', 'frontend', 'public', 'images'),
    'images',
    os.path.join('frontend', 'public', 'images'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'public', 'images'),
    os.path.join('..', 'public', 'images'),
    os.path.join(os.getcwd(), 'images'),
    os.path.join(os.getcwd(), '..', 'frontend', 'public', 'images')
]

# Find the first valid images directory
IMAGES_DIR = None
for path in POSSIBLE_IMAGE_DIRS:
    if os.path.exists(path):
        IMAGES_DIR = os.path.abspath(path)
        logger.info(f"Found images directory at: {IMAGES_DIR}")
        break

if not IMAGES_DIR:
    logger.warning("Could not find any valid images directory!")
    logger.info(f"Searched: {POSSIBLE_IMAGE_DIRS}")
    logger.info(f"Current working directory: {os.getcwd()}")
    IMAGES_DIR = "images"  # Fallback

# Initialize database connection
db = Neo4jConnection()

# Cache for image existence checks to reduce filesystem lookups
IMAGE_EXISTENCE_CACHE = {}
# Cache for missing image requests to avoid excessive logging
MISSING_IMAGE_CACHE = set()

# Generate a small placeholder image
def generate_placeholder_image(color='#FF9999', size=(100, 100)):
    """Generate a base64 data URL for a placeholder image"""
    from PIL import Image, ImageDraw
    img = Image.new('RGB', size, color=color)
    draw = ImageDraw.Draw(img)
    
    # Draw a border
    border_color = '#CC0000'
    draw.rectangle([(0, 0), (size[0]-1, size[1]-1)], outline=border_color, width=4)
    
    # Convert to base64
    import io
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{img_str}"

# Helper function to normalize image paths
def normalize_image_path(path):
    """Extract just the filename from any path format"""
    if path is None:
        return None
    
    # Remove any "images/" prefix
    if path.startswith('images/'):
        path = path[7:]  # Remove "images/" prefix
        
    # Get just the filename without any path
    return os.path.basename(path)

# Check if an image exists on disk
def image_exists(filename):
    """Check if an image exists in the images directory"""
    if filename in IMAGE_EXISTENCE_CACHE:
        return IMAGE_EXISTENCE_CACHE[filename]
        
    # Check direct match
    full_path = os.path.join(IMAGES_DIR, filename)
    exists = os.path.exists(full_path)
    
    if not exists:
        # Try case-insensitive matching
        try:
            for f in os.listdir(IMAGES_DIR):
                if f.lower() == filename.lower():
                    exists = True
                    break
        except Exception:
            pass
    
    # Cache the result
    IMAGE_EXISTENCE_CACHE[filename] = exists
    return exists

# Endpoint to view logs
@app.route('/admin/logs')
def view_logs():
    level = request.args.get('level', None)
    limit = int(request.args.get('limit', 100))
    format_type = request.args.get('format', 'html')
    
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
    
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Application Logs</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
                tr:hover { background-color: #f5f5f5; }
                .controls { margin-bottom: 20px; }
                button { padding: 8px 12px; margin-right: 10px; }
            </style>
        </head>
        <body>
            <h1>Application Logs</h1>
            <div class="controls">
                <button onclick="window.location.href='/admin/logs'">All Logs</button>
                <button onclick="window.location.href='/admin/logs?level=ERROR'">Errors Only</button>
                <button onclick="window.location.href='/admin/logs?level=WARNING'">Warnings Only</button>
                <button onclick="window.location.href='/admin/logs?level=INFO'">Info Only</button>
                <button onclick="clearLogs()">Clear Logs</button>
                <button onclick="window.location.href='/admin'">Back to Admin</button>
            </div>
            <table>
                <tr>
                    <th>Timestamp</th>
                    <th>Level</th>
                    <th>Message</th>
                </tr>
                {{ logs_html | safe }}
            </table>
            <script>
                function clearLogs() {
                    if (confirm('Are you sure you want to clear all logs?')) {
                        fetch('/admin/logs/clear', { method: 'POST' })
                            .then(response => response.json())
                            .then(data => {
                                if (data.status === 'ok') {
                                    window.location.reload();
                                }
                            });
                    }
                }
            </script>
        </body>
        </html>
    """, logs_html=logs_html)

# Endpoint to clear logs
@app.route('/admin/logs/clear', methods=['POST'])
def clear_logs():
    memory_handler.clear()
    return jsonify({"status": "ok"})

# Endpoint to provide a placeholder image for missing images
@app.route('/placeholder/<color>')
def placeholder_image(color='FF9999'):
    """Return a placeholder image for missing images"""
    try:
        # Clean the color input
        color = color.strip('#')
        if len(color) == 6:
            color = f"#{color}"
        else:
            color = "#FF9999"  # Default fallback
            
        # Generate the image 
        img_data = generate_placeholder_image(color)
        # Strip the data:image/png;base64, prefix
        img_data = img_data.split(',')[1]
        
        # Convert base64 to binary
        img_binary = base64.b64decode(img_data)
        
        # Return as an actual image
        response = app.response_class(
            response=img_binary,
            status=200,
            mimetype='image/png'
        )
        return response
    except Exception as e:
        logger.error(f"Error generating placeholder: {e}")
        return "Error", 500

# Debug endpoint to list all available images
@app.route('/debug/images')
def list_images():
    """List all available images in the configured directory"""
    if not os.path.exists(IMAGES_DIR):
        return jsonify({
            "error": f"Images directory not found: {IMAGES_DIR}",
            "cwd": os.getcwd(),
            "tried_paths": POSSIBLE_IMAGE_DIRS
        }), 404
    
    # List all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
        image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
        image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext.upper())))
    
    # Format the results
    images = [os.path.basename(f) for f in image_files]
    
    return jsonify({
        "images_dir": IMAGES_DIR,
        "image_count": len(images),
        "images": images
    })

# Debug endpoint to compare DB images with filesystem
@app.route('/debug/sync')
def debug_sync():
    """Compare database images with filesystem images"""
    try:
        # Get images from database
        db_images = db.get_all_images()
        
        # Get images from filesystem
        fs_images = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            fs_images.extend([os.path.basename(f) for f in glob.glob(os.path.join(IMAGES_DIR, ext))])
            fs_images.extend([os.path.basename(f) for f in glob.glob(os.path.join(IMAGES_DIR, ext.upper()))])
        
        # Normalize all paths to just filenames
        db_images = [normalize_image_path(img) for img in db_images]
        fs_images = [normalize_image_path(img) for img in fs_images]
        
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
        return jsonify({
            "error": str(e)
        }), 500

# Debug endpoint to test Neo4j connection
@app.route('/debug/db')
def debug_db():
    """Check Neo4j database connection and contents"""
    try:
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
        return jsonify({
            "connection": "ERROR",
            "error": str(e)
        }), 500

# Reset and repopulate the database
@app.route('/admin/reset-db', methods=['POST'])
def reset_db():
    """Reset and repopulate the database from the images directory"""
    try:
        if not os.path.exists(IMAGES_DIR):
            return jsonify({
                "error": f"Images directory not found: {IMAGES_DIR}"
            }), 404
            
        # Count images before populating
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            image_files.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
        
        if not image_files:
            return jsonify({
                "error": f"No images found in directory: {IMAGES_DIR}"
            }), 404
            
        # Populate the graph
        populate_graph(IMAGES_DIR)
        
        # Clear image existence cache after repopulating
        IMAGE_EXISTENCE_CACHE.clear()
        MISSING_IMAGE_CACHE.clear()
        
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

# Fix database by pruning missing image nodes
@app.route('/admin/fix-db', methods=['POST'])
def fix_db():
    """Remove nodes for images that don't exist in the filesystem"""
    try:
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
            MISSING_IMAGE_CACHE.clear()
            
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

# API endpoint to get neighbors
@app.route('/neighbors', methods=['GET'])
def get_neighbors():
    image_path = request.args.get('image_path')
    similarity_threshold = float(request.args.get('threshold', 0.7))
    limit = int(request.args.get('limit', 20))

    if not image_path:
        return jsonify({"error": "image_path is required"}), 400
        
    # First try with the path as provided
    graph_data = db.get_neighbors(image_path, similarity_threshold, limit)
    
    # If no center node found, try alternative path formats
    if not graph_data.get('nodes'):
        logger.info(f"No center node found for path: {image_path}, trying alternatives")
        
        # Try without 'images/' prefix
        if image_path.startswith('images/'):
            alt_path = image_path[7:]
            graph_data = db.get_neighbors(alt_path, similarity_threshold, limit)
            if graph_data.get('nodes'):
                logger.info(f"Found center node with alternative path: {alt_path}")
        
        # Try with 'images/' prefix
        if not graph_data.get('nodes') and not image_path.startswith('images/'):
            alt_path = f"images/{image_path}"
            graph_data = db.get_neighbors(alt_path, similarity_threshold, limit)
            if graph_data.get('nodes'):
                logger.info(f"Found center node with alternative path: {alt_path}")
                
        # Try with just the filename
        if not graph_data.get('nodes'):
            filename = normalize_image_path(image_path)
            graph_data = db.get_neighbors(filename, similarity_threshold, limit)
            if graph_data.get('nodes'):
                logger.info(f"Found center node with filename: {filename}")
    
    # Log the output at info level
    logger.info(f"Returning data with {len(graph_data.get('nodes', []))} nodes and {len(graph_data.get('edges', []))} edges")
    
    # Filter out nodes for images that don't exist
    nodes_to_keep = []
    removed_nodes = []
    for node in graph_data.get('nodes', []):
        filename = normalize_image_path(node['path'])
        if image_exists(filename) or node.get('isCenter'):
            nodes_to_keep.append(node)
        else:
            removed_nodes.append(filename)
    
    # Only log filtered nodes if there are some and not too many
    if removed_nodes and len(removed_nodes) <= 5:
        logger.info(f"Filtered out nodes for missing images: {', '.join(removed_nodes)}")
    elif removed_nodes:
        logger.info(f"Filtered out {len(removed_nodes)} nodes for missing images")
    
    # Update edges to only include existing nodes
    node_ids = {node['id'] for node in nodes_to_keep}
    edges_to_keep = []
    for edge in graph_data.get('edges', []):
        if edge['source'] in node_ids and edge['target'] in node_ids:
            edges_to_keep.append(edge)
    
    # Return filtered data
    filtered_data = {
        'nodes': nodes_to_keep,
        'edges': edges_to_keep
    }
    
    return jsonify(filtered_data)

# Improved static file serving with better error handling
@app.route('/static/<path:filename>')
def serve_image(filename):
    # Clean up filename and remove any path components
    filename = normalize_image_path(filename)
    
    # Security check to prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid file path", 400
    
    # Skip cache check and logging for images we know don't exist
    if filename in MISSING_IMAGE_CACHE:
        return redirect('/placeholder/FF9999', code=303)
    
    # Look for the file with case-insensitive matching
    real_filename = None
    if os.path.exists(os.path.join(IMAGES_DIR, filename)):
        real_filename = filename
    else:
        # Try to find the file with case-insensitive matching
        try:
            for f in os.listdir(IMAGES_DIR):
                if f.lower() == filename.lower():
                    real_filename = f
                    logger.debug(f"Found case-insensitive match: {f}")
                    break
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
    
    if not real_filename:
        # Only log the first occurrence of each missing image
        if filename not in MISSING_IMAGE_CACHE:
            logger.warning(f"Image not found: {filename}")
            MISSING_IMAGE_CACHE.add(filename)
        
        # Redirect to placeholder
        return redirect('/placeholder/FF9999', code=303)
        
    # Log successful requests at debug level
    logger.debug(f"Serving image: {real_filename}")
    
    # Set cache control to prevent caching issues
    response = send_from_directory(IMAGES_DIR, real_filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Simple HTML admin dashboard
@app.route('/admin')
def admin_dashboard():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Similarity Explorer Admin</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            button { padding: 10px; margin: 10px 0; cursor: pointer; }
            .card { border: 1px solid #ccc; padding: 15px; margin: 15px 0; border-radius: 5px; }
            pre { background: #f5f5f5; padding: 10px; overflow: auto; }
            .logs-teaser { max-height: 150px; overflow: auto; font-family: monospace; font-size: 12px; }
        </style>
    </head>
    <body>
        <h1>Image Similarity Explorer Admin</h1>
        
        <div class="card">
            <h2>Database Management</h2>
            <button id="resetDb">Reset Database & Repopulate</button>
            <button id="fixDb">Fix Database (Remove Missing Images)</button>
            <div id="resetResult"></div>
        </div>
        
        <div class="card">
            <h2>Database/Filesystem Sync</h2>
            <button id="checkSync">Check Sync Status</button>
            <div id="syncResult"></div>
        </div>
        
        <div class="card">
            <h2>Image Directory</h2>
            <button id="listImages">List Available Images</button>
            <div id="imagesResult"></div>
        </div>
        
        <div class="card">
            <h2>Database Status</h2>
            <button id="checkDb">Check Database</button>
            <div id="dbResult"></div>
        </div>
        
        <div class="card">
            <h2>Application Logs</h2>
            <div class="logs-teaser" id="logsTeaser">Loading recent logs...</div>
            <button onclick="window.location.href='/admin/logs'">View All Logs</button>
            <button onclick="window.location.href='/admin/logs?level=ERROR'">View Errors</button>
            <button onclick="refreshLogs()">Refresh</button>
        </div>
        
        <script>
            // Fetch recent logs for the teaser
            async function refreshLogs() {
                try {
                    const response = await fetch('/admin/logs?format=json&limit=10');
                    const logs = await response.json();
                    
                    const logsHtml = logs.map(log => 
                        `<div style="${getLogStyle(log.level)}">${log.timestamp} - ${log.level} - ${log.message}</div>`
                    ).join('');
                    
                    document.getElementById('logsTeaser').innerHTML = logsHtml || 'No logs available';
                } catch (error) {
                    document.getElementById('logsTeaser').innerHTML = `Error loading logs: ${error.message}`;
                }
            }
            
            function getLogStyle(level) {
                switch(level) {
                    case 'ERROR': return 'color: red;';
                    case 'WARNING': return 'color: orange;';
                    case 'INFO': return 'color: green;';
                    default: return '';
                }
            }
            
            document.getElementById('resetDb').addEventListener('click', async () => {
                if (confirm('This will RESET the entire database and rebuild it from the images directory. Continue?')) {
                    try {
                        const result = document.getElementById('resetResult');
                        result.innerHTML = 'Processing...';
                        
                        const response = await fetch('/admin/reset-db', { method: 'POST' });
                        const data = await response.json();
                        
                        result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                        refreshLogs();
                    } catch (error) {
                        document.getElementById('resetResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
                    }
                }
            });
            
            document.getElementById('fixDb').addEventListener('click', async () => {
                if (confirm('This will remove database nodes for images that don\\'t exist in the filesystem. Continue?')) {
                    try {
                        const result = document.getElementById('resetResult');
                        result.innerHTML = 'Processing...';
                        
                        const response = await fetch('/admin/fix-db', { method: 'POST' });
                        const data = await response.json();
                        
                        result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                        refreshLogs();
                    } catch (error) {
                        document.getElementById('resetResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
                    }
                }
            });
            
            document.getElementById('checkSync').addEventListener('click', async () => {
                try {
                    const result = document.getElementById('syncResult');
                    result.innerHTML = 'Loading...';
                    
                    const response = await fetch('/debug/sync');
                    const data = await response.json();
                    
                    result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch (error) {
                    document.getElementById('syncResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
                }
            });
            
            document.getElementById('listImages').addEventListener('click', async () => {
                try {
                    const result = document.getElementById('imagesResult');
                    result.innerHTML = 'Loading...';
                    
                    const response = await fetch('/debug/images');
                    const data = await response.json();
                    
                    result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch (error) {
                    document.getElementById('imagesResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
                }
            });
            
            document.getElementById('checkDb').addEventListener('click', async () => {
                try {
                    const result = document.getElementById('dbResult');
                    result.innerHTML = 'Loading...';
                    
                    const response = await fetch('/debug/db');
                    const data = await response.json();
                    
                    result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch (error) {
                    document.getElementById('dbResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
                }
            });
            
            // Initial logs load
            refreshLogs();
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/')
def index():
    return "Image similarity API - Visit /admin for management"

if __name__ == '__main__':
    # List available images to help with troubleshooting
    if os.path.exists(IMAGES_DIR):
        logger.info(f"Available images in {IMAGES_DIR}:")
        image_count = 0
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            for img in glob.glob(os.path.join(IMAGES_DIR, ext)):
                if image_count < 10:  # Only print the first 10 images
                    logger.info(f" - {os.path.basename(img)}")
                image_count += 1
        if image_count > 10:
            logger.info(f" ... and {image_count - 10} more images")
        logger.info(f"Total images found: {image_count}")
    else:
        logger.warning(f"WARNING: Image directory '{IMAGES_DIR}' not found")
    
    # Start the application
    logger.info("Starting Flask application...")
    app.run(debug=True, port=5001)