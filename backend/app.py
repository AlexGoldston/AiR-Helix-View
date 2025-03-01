from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from graph import Neo4jConnection
import os

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})  # Allow all origins

# Configure the images directory path
IMAGES_DIR = os.path.join('..', 'frontend', 'public', 'images')  # Path relative to the backend directory
if not os.path.exists(IMAGES_DIR):
    print(f"WARNING: Image directory '{IMAGES_DIR}' not found. Current working directory: {os.getcwd()}")
    # Try to find the images directory in common locations
    possible_paths = [
        'images',
        os.path.join('frontend', 'public', 'images'),
        os.path.join('..', 'frontend', 'public', 'images'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'public', 'images')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            IMAGES_DIR = path
            print(f"Found images directory at: {os.path.abspath(IMAGES_DIR)}")
            break
else:
    print(f"Found images directory at: {os.path.abspath(IMAGES_DIR)}")

db = Neo4jConnection() # initiate db connection

@app.route('/neighbors', methods=['GET'])
def get_neighbors():
    image_path = request.args.get('image_path')
    similarity_threshold = float(request.args.get('threshold', 0.7))
    limit = int(request.args.get('limit', 20))

    if not image_path:
        return jsonify({"error": "image_path is required"}), 400

    graph_data = db.get_neighbors(image_path, similarity_threshold, limit)
    
    # Debug the output
    print(f"Returning data with {len(graph_data.get('nodes', []))} nodes and {len(graph_data.get('edges', []))} edges")
    
    return jsonify(graph_data)

# Improved static file serving with better error handling
@app.route('/static/<path:filename>')
def serve_image(filename):
    # Security check to prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid file path", 400
        
    # Check if file exists
    full_path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(full_path):
        print(f"Image not found: {full_path}")
        return "Image not found", 404
        
    # Log successful requests
    print(f"Serving image: {full_path}")
    
    # Set cache control to prevent caching issues
    response = send_from_directory(IMAGES_DIR, filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    return "Image similarity API"

if __name__ == '__main__':
    # List available images to help with troubleshooting
    if os.path.exists(IMAGES_DIR):
        print(f"Available images in {IMAGES_DIR}:")
        image_count = 0
        for img in os.listdir(IMAGES_DIR):
            if img.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                if image_count < 10:  # Only print the first 10 images
                    print(f" - {img}")
                image_count += 1
        if image_count > 10:
            print(f" ... and {image_count - 10} more images")
        print(f"Total images found: {image_count}")
    else:
        print(f"WARNING: Image directory '{IMAGES_DIR}' not found")
    
    app.run(debug=True, port=5001)