from flask import Flask, jsonify, request, send_from_directory, render_template_string
from flask_cors import CORS
from graph import Neo4jConnection, populate_graph
import os
import glob

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
        print(f"Found images directory at: {IMAGES_DIR}")
        break

if not IMAGES_DIR:
    print("WARNING: Could not find any valid images directory!")
    print(f"Searched: {POSSIBLE_IMAGE_DIRS}")
    print(f"Current working directory: {os.getcwd()}")
    IMAGES_DIR = "images"  # Fallback

# Initialize database connection
db = Neo4jConnection()

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
        
        return jsonify({
            "status": "OK",
            "message": f"Database reset and populated with {len(image_files)} images"
        })
    except Exception as e:
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
        print(f"No center node found for path: {image_path}, trying alternatives")
        
        # Try without 'images/' prefix
        if image_path.startswith('images/'):
            alt_path = image_path[7:]
            graph_data = db.get_neighbors(alt_path, similarity_threshold, limit)
            if graph_data.get('nodes'):
                print(f"Found center node with alternative path: {alt_path}")
        
        # Try with 'images/' prefix
        if not graph_data.get('nodes') and not image_path.startswith('images/'):
            alt_path = f"images/{image_path}"
            graph_data = db.get_neighbors(alt_path, similarity_threshold, limit)
            if graph_data.get('nodes'):
                print(f"Found center node with alternative path: {alt_path}")
                
        # Try with just the filename
        if not graph_data.get('nodes'):
            filename = normalize_image_path(image_path)
            graph_data = db.get_neighbors(filename, similarity_threshold, limit)
            if graph_data.get('nodes'):
                print(f"Found center node with filename: {filename}")
    
    # Debug the output
    print(f"Returning data with {len(graph_data.get('nodes', []))} nodes and {len(graph_data.get('edges', []))} edges")
    
    return jsonify(graph_data)

# Improved static file serving with better error handling
@app.route('/static/<path:filename>')
def serve_image(filename):
    # Clean up filename and remove any path components
    filename = normalize_image_path(filename)
    
    print(f"Request for image: {filename}")
    
    # Security check to prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid file path", 400
    
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
                    print(f"Found case-insensitive match: {f}")
                    break
        except Exception as e:
            print(f"Error listing directory: {e}")
    
    if not real_filename:
        print(f"Image not found: {filename}")
        try:
            available_files = os.listdir(IMAGES_DIR)
            print(f"Available files in directory ({len(available_files)} total): {available_files[:10]}")
        except Exception as e:
            print(f"Error listing directory: {e}")
        return "Image not found", 404
        
    # Log successful requests
    print(f"Serving image: {real_filename} from {IMAGES_DIR}")
    
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
        </style>
    </head>
    <body>
        <h1>Image Similarity Explorer Admin</h1>
        
        <div class="card">
            <h2>Database Management</h2>
            <button id="resetDb">Reset Database & Repopulate</button>
            <div id="resetResult"></div>
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
        
        <script>
            document.getElementById('resetDb').addEventListener('click', async () => {
                if (confirm('This will RESET the entire database and rebuild it from the images directory. Continue?')) {
                    try {
                        const result = document.getElementById('resetResult');
                        result.innerHTML = 'Processing...';
                        
                        const response = await fetch('/admin/reset-db', { method: 'POST' });
                        const data = await response.json();
                        
                        result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    } catch (error) {
                        document.getElementById('resetResult').innerHTML = `<pre>Error: ${error.message}</pre>`;
                    }
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
        print(f"Available images in {IMAGES_DIR}:")
        image_count = 0
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif']:
            for img in glob.glob(os.path.join(IMAGES_DIR, ext)):
                if image_count < 10:  # Only print the first 10 images
                    print(f" - {os.path.basename(img)}")
                image_count += 1
        if image_count > 10:
            print(f" ... and {image_count - 10} more images")
        print(f"Total images found: {image_count}")
    else:
        print(f"WARNING: Image directory '{IMAGES_DIR}' not found")
    
    app.run(debug=True, port=5001)