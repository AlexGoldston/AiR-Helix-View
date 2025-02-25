from flask import Flask, jsonify, request
from flask_cors import CORS
from graph import Neo4jConnection

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

db = Neo4jConnection() #initiate db connection

@app.route('/neighbors', methods=['GET'])
def get_neighbors():
    image_path = request.args.get('image_path')
    similarity_threshold = float(request.args.get('threshold', 0.7))
    limit = int(request.args.get('limit', 20))

    if not image_path:
        return jsonify({"error": "image_path is required"}), 400

    graph_data = db.get_neighbors(image_path, similarity_threshold, limit)
    return jsonify(graph_data)

@app.route('/')
def index():
  return "Image similarity API"

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Run on a different port than the React app