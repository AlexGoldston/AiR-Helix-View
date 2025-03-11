from flask import Blueprint, jsonify, request
import logging
import traceback
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

@api_bp.route('/debug/relationships')
def debug_relationships():
    """Get information about relationships in the database"""
    db = get_db_connection()
    
    try:
        # Count all relationships
        total_count = 0
        image_path = request.args.get('image_path', 'allianz_stadium_sydney01.jpg')
        image_count = 0
        samples = []
        
        with db.driver.session() as session:
            # Count all relationships
            total_result = session.run("MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) as count")
            total_record = total_result.single()
            if total_record:
                total_count = total_record["count"]
            
            # Count relationships for this specific image
            image_result = session.run(
                """
                MATCH (img:Image {path: $path})-[r:SIMILAR_TO]-() 
                RETURN count(r) as count
                """, 
                path=image_path
            )
            image_record = image_result.single()
            if image_record:
                image_count = image_record["count"]
            
            # Get sample relationships
            if image_count > 0:
                samples_result = session.run(
                    """
                    MATCH (img:Image {path: $path})-[r:SIMILAR_TO]-(other:Image)
                    RETURN img.path as source, other.path as target, r.similarity as similarity
                    ORDER BY r.similarity DESC
                    LIMIT 10
                    """,
                    path=image_path
                )
                
                for record in samples_result:
                    samples.append({
                        "source": record["source"],
                        "target": record["target"],
                        "similarity": record["similarity"]
                    })
        
        # Check if the image exists
        image_exists = False
        with db.driver.session() as session:
            existence_result = session.run(
                "MATCH (img:Image {path: $path}) RETURN count(img) as count",
                path=image_path
            )
            existence_record = existence_result.single()
            if existence_record and existence_record["count"] > 0:
                image_exists = True
        
        return jsonify({
            "total_relationships": total_count,
            "image": image_path,
            "image_exists": image_exists,
            "relationships_for_image": image_count,
            "samples": samples
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return jsonify({"error": str(e), "details": error_details}), 500

@api_bp.route('/debug/threshold-test')
def test_threshold():
    """Test different similarity thresholds"""
    db = get_db_connection()
    
    try:
        image_path = request.args.get('image_path', 'allianz_stadium_sydney01.jpg')
        results = {}
        
        # Test different thresholds
        thresholds = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05]
        
        with db.driver.session() as session:
            for threshold in thresholds:
                count_result = session.run(
                    """
                    MATCH (img:Image {path: $path})-[r:SIMILAR_TO]-(other:Image)
                    WHERE r.similarity >= $threshold
                    RETURN count(other) as count
                    """,
                    path=image_path,
                    threshold=threshold
                )
                
                record = count_result.single()
                count = record["count"] if record else 0
                results[str(threshold)] = count
        
        # Check if the image exists
        image_exists = False
        with db.driver.session() as session:
            existence_result = session.run(
                "MATCH (img:Image {path: $path}) RETURN count(img) as count",
                path=image_path
            )
            existence_record = existence_result.single()
            if existence_record and existence_record["count"] > 0:
                image_exists = True
        
        return jsonify({
            "image": image_path,
            "image_exists": image_exists,
            "threshold_counts": results
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return jsonify({"error": str(e), "details": error_details}), 500

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

@api_bp.route('/search', methods=['GET'])
def search_images():
    """Search for images based on text description"""
    query = request.args.get('query')
    limit = int(request.args.get('limit', 10))
    
    if not query:
        return jsonify({"error": "query parameter is required"}), 400
        
    # Get database connection
    db = get_db_connection()
    
    # Search by text
    results = db.search_images_by_text(query, limit=limit)
    
    # Format the results
    formatted_results = []
    for result in results:
        formatted_result = {
            "id": result.get("id"),
            "path": result.get("path"),
            "description": result.get("description", "No description available")
        }
        formatted_results.append(formatted_result)
    
    return jsonify({
        "query": query,
        "results": formatted_results,
        "count": len(formatted_results)
    })

@api_bp.route('/features', methods=['GET'])
def get_available_features():
    """Get a summary of available features for filtering/searching"""
    db = get_db_connection()
    
    try:
        # Get top tags
        with db.driver.session() as session:
            # Get tag counts
            tag_result = session.run("""
                MATCH (t:Tag)<-[:HAS_TAG]-(i:Image)
                WITH t.name AS tag, COUNT(i) AS count
                WHERE count >= 3  // Only include tags that appear at least 3 times
                RETURN tag, count
                ORDER BY count DESC
                LIMIT 50
            """)
            
            tags = [{"name": record["tag"], "count": record["count"]} for record in tag_result]
            
            # Get color counts
            color_result = session.run("""
                MATCH (c:Color)<-[:HAS_COLOR]-(i:Image)
                WITH c.name AS color, COUNT(i) AS count
                RETURN color, count
                ORDER BY count DESC
            """)
            
            colors = [{"name": record["color"], "count": record["count"]} for record in color_result]
            
            # Get object counts
            object_result = session.run("""
                MATCH (o:Object)<-[:CONTAINS]-(i:Image)
                WITH o.name AS object, COUNT(i) AS count
                WHERE count >= 2  // Only include objects that appear at least twice
                RETURN object, count
                ORDER BY count DESC
                LIMIT 30
            """)
            
            objects = [{"name": record["object"], "count": record["count"]} for record in object_result]
            
            # Get camera models
            camera_result = session.run("""
                MATCH (c:Camera)<-[:TAKEN_WITH]-(i:Image)
                WITH c.model AS camera, COUNT(i) AS count
                RETURN camera, count
                ORDER BY count DESC
            """)
            
            cameras = [{"model": record["camera"], "count": record["count"]} for record in camera_result]
            
            # Get image orientations
            orientation_result = session.run("""
                MATCH (i:Image)
                WHERE i.basic_orientation IS NOT NULL
                RETURN i.basic_orientation AS orientation, COUNT(i) AS count
                ORDER BY count DESC
            """)
            
            orientations = [{"name": record["orientation"], "count": record["count"]} for record in orientation_result]
        
        # Compile all feature data
        feature_data = {
            "tags": tags,
            "colors": colors,
            "objects": objects,
            "cameras": cameras,
            "orientations": orientations
        }
        
        return jsonify(feature_data)
        
    except Exception as e:
        logger.error(f"Error getting feature data: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Failed to retrieve feature data"}), 500

@api_bp.route('/search/advanced', methods=['GET', 'POST'])
def advanced_search():
    """
    Advanced search endpoint that combines multiple feature criteria
    
    Supports both GET with query parameters and POST with JSON body
    
    Query Parameters / JSON Body:
    - tags: comma-separated list of tags (GET) or array of tags (POST)
    - tags_operator: "AND" or "OR" (default: "AND")
    - colors: comma-separated list of colors (GET) or array of colors (POST)
    - colors_operator: "AND" or "OR" (default: "OR")
    - objects: comma-separated list of objects (GET) or array of objects (POST)
    - objects_operator: "AND" or "OR" (default: "OR")
    - min_confidence: minimum confidence for object detection (default: 0.5)
    - orientation: image orientation (landscape, portrait, square)
    - camera: camera model
    - limit: maximum number of results (default: 50)
    """
    try:
        # Get search criteria from request
        if request.method == 'POST':
            # For POST requests, get criteria from JSON body
            criteria = request.json
        else:
            # For GET requests, get criteria from query parameters
            criteria = {}
            
            # Process tags
            tags = request.args.get('tags')
            if tags:
                criteria['tags'] = [tag.strip() for tag in tags.split(',')]
                criteria['tags_operator'] = request.args.get('tags_operator', 'AND').upper()
            
            # Process colors
            colors = request.args.get('colors')
            if colors:
                criteria['colors'] = [color.strip() for color in colors.split(',')]
                criteria['colors_operator'] = request.args.get('colors_operator', 'OR').upper()
            
            # Process objects
            objects = request.args.get('objects')
            if objects:
                criteria['objects'] = [obj.strip() for obj in objects.split(',')]
                criteria['objects_operator'] = request.args.get('objects_operator', 'OR').upper()
                
                # Get min confidence for object detection
                min_confidence = request.args.get('min_confidence')
                if min_confidence:
                    criteria['min_confidence'] = float(min_confidence)
            
            # Process orientation
            orientation = request.args.get('orientation')
            if orientation:
                criteria['orientation'] = orientation
            
            # Process camera
            camera = request.args.get('camera')
            if camera:
                criteria['camera'] = camera
        
        # Get limit parameter
        limit = int(request.args.get('limit', 50))
        
        # Validate criteria
        if not criteria:
            return jsonify({"error": "No search criteria provided"}), 400
        
        # Get database connection
        db = get_db_connection()
        
        # Perform the search
        results = db.search_images_by_features(criteria, limit=limit)
        
        # Format the results with full URLs
        formatted_results = []
        for path in results:
            formatted_results.append({
                "path": path,
                "url": f"/static/{path}"
            })
        
        return jsonify({
            "criteria": criteria,
            "results": formatted_results,
            "count": len(formatted_results)
        })
        
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

@api_bp.route('/debug/db-status')
def db_status():
    """Get basic database statistics"""
    db = get_db_connection()
    
    try:
        stats = {}
        
        with db.driver.session() as session:
            # Count nodes
            node_result = session.run("MATCH (n:Image) RETURN count(n) as count")
            node_record = node_result.single()
            stats["image_count"] = node_record["count"] if node_record else 0
            
            # Count relationships
            rel_result = session.run("MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) as count")
            rel_record = rel_result.single()
            stats["relationship_count"] = rel_record["count"] if rel_record else 0
            
            # Get a few sample image paths
            samples_result = session.run("MATCH (n:Image) RETURN n.path as path LIMIT 5")
            stats["sample_images"] = [record["path"] for record in samples_result]
        
        # Add database status information
        stats["database_status"] = "empty" if stats["image_count"] == 0 else "populated"
        stats["needs_rebuild"] = stats["relationship_count"] == 0 and stats["image_count"] > 0
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/search/tags', methods=['GET'])
def search_by_tags():
    """Search for images with specific tags"""
    tags = request.args.get('tags')
    operator = request.args.get('operator', 'AND').upper()
    limit = int(request.args.get('limit', 50))
    
    if not tags:
        return jsonify({"error": "tags parameter is required"}), 400
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',')]
    
    # Get database connection
    db = get_db_connection()
    
    # Perform the search
    results = db.get_images_by_tags(tag_list, operator=operator, limit=limit)
    
    # Format the results
    formatted_results = [{"path": path, "url": f"/static/{path}"} for path in results]
    
    return jsonify({
        "tags": tag_list,
        "operator": operator,
        "results": formatted_results,
        "count": len(formatted_results)
    })

@api_bp.route('/search/color', methods=['GET'])
def search_by_color():
    """Search for images with a specific color"""
    color = request.args.get('color')
    limit = int(request.args.get('limit', 50))
    
    if not color:
        return jsonify({"error": "color parameter is required"}), 400
    
    # Get database connection
    db = get_db_connection()
    
    # Perform the search
    results = db.get_images_by_color(color, limit=limit)
    
    # Format the results
    formatted_results = [{"path": path, "url": f"/static/{path}"} for path in results]
    
    return jsonify({
        "color": color,
        "results": formatted_results,
        "count": len(formatted_results)
    })

@api_bp.route('/search/object', methods=['GET'])
def search_by_object():
    """Search for images containing a specific object"""
    object_name = request.args.get('object')
    min_confidence = float(request.args.get('min_confidence', 0.5))
    limit = int(request.args.get('limit', 50))
    
    if not object_name:
        return jsonify({"error": "object parameter is required"}), 400
    
    # Get database connection
    db = get_db_connection()
    
    # Perform the search
    results = db.get_images_containing_object(object_name, min_confidence=min_confidence, limit=limit)
    
    # Format the results
    formatted_results = [{
        "path": result["path"], 
        "url": f"/static/{result['path']}",
        "confidence": result["confidence"]
    } for result in results]
    
    return jsonify({
        "object": object_name,
        "min_confidence": min_confidence,
        "results": formatted_results,
        "count": len(formatted_results)
    })