from flask import Blueprint, jsonify, request
import logging
from database import get_db_connection
from utils.image_utils import image_exists, normalize_image_path, MISSING_IMAGE_CACHE
from config import DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_NEIGHBOR_LIMIT

logger = logging.getLogger('image-similarity')
api_bp = Blueprint('api', __name__)

@api_bp.route('/neighbors', methods=['GET'])
def get_neighbors():
    """Get similar image neighbors based on image embeddings"""
    image_path = request.args.get('image_path')
    similarity_threshold = float(request.args.get('threshold', DEFAULT_SIMILARITY_THRESHOLD))
    limit = int(request.args.get('limit', DEFAULT_NEIGHBOR_LIMIT))

    if not image_path:
        return jsonify({"error": "image_path is required"}), 400
        
    # Get database connection
    db = get_db_connection()
    
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
    
    # Log the output
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

@api_bp.route('/extended-neighbors', methods=['GET'])
def get_extended_neighbors():
    """Get multi-level similar image network"""
    image_path = request.args.get('image_path')
    similarity_threshold = float(request.args.get('threshold', DEFAULT_SIMILARITY_THRESHOLD))
    depth = int(request.args.get('depth', 1))
    limit_per_level = int(request.args.get('limit_per_level', 10))
    max_nodes = int(request.args.get('max_nodes', 100))

    if not image_path:
        return jsonify({"error": "image_path is required"}), 400
        
    # Get database connection
    db = get_db_connection()
    
    # Get extended network
    graph_data = db.get_extended_neighbors(
        image_path, 
        similarity_threshold, 
        depth=depth,
        limit_per_level=limit_per_level,
        max_nodes=max_nodes
    )
    
    # Filter out nodes for images that don't exist
    nodes_to_keep = []
    for node in graph_data.get('nodes', []):
        filename = normalize_image_path(node['path'])
        if image_exists(filename) or node.get('isCenter'):
            nodes_to_keep.append(node)
    
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