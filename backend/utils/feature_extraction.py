# backend/utils/feature_extraction.py
import os
import logging
import traceback
import time
from PIL import Image
import numpy as np
from collections import Counter
import colorsys
import math

# Check if optional libraries are available
OPENCV_AVAILABLE = False
TENSORFLOW_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    pass

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger('image-similarity')

class ImageFeatureExtractor:
    """Extract various visual features from images for improved search and filtering"""
    
    def __init__(self, use_ml_features=True):
        """
        Initialize the feature extractor
        
        Args:
            use_ml_features (bool): Whether to use ML-based feature extraction if available
        """
        self.use_ml_features = use_ml_features
        self.ml_models = {}
        
        # Initialize ML models if requested and available
        if use_ml_features:
            self._initialize_ml_models()
            
        logger.info(f"Feature extractor initialized. ML features: {use_ml_features}")
    
    def _initialize_ml_models(self):
        """Initialize machine learning models for feature extraction"""
        # Track which features we can extract with ML
        self.available_ml_features = []
        
        # Initialize object detection if TensorFlow is available
        if TENSORFLOW_AVAILABLE:
            try:
                # Load model for object detection
                # Using a small and fast model for demonstration
                model_name = "efficientdet/lite0/detection"
                
                logger.info(f"Loading TensorFlow Hub model: {model_name}")
                
                try:
                    import tensorflow_hub as hub
                    detector = hub.load(f"https://tfhub.dev/tensorflow/lite-model/{model_name}/1")
                    self.ml_models['object_detector'] = detector
                    self.available_ml_features.append('objects')
                    logger.info("Object detection model loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load object detection model: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize TensorFlow models: {e}")
        
        # Initialize OpenCV-based models
        if OPENCV_AVAILABLE:
            try:
                # Face detection using Haar Cascades (simple but effective)
                face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                if os.path.exists(face_cascade_path):
                    self.ml_models['face_detector'] = cv2.CascadeClassifier(face_cascade_path)
                    self.available_ml_features.append('faces')
                    logger.info("Face detection model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenCV models: {e}")
        
        logger.info(f"ML feature extraction available for: {', '.join(self.available_ml_features)}")
    
    def extract_features(self, image_path):
        """
        Extract all available features from an image
        
        Args:
            image_path (str): Path to the image
            
        Returns:
            dict: Dictionary of extracted features and tags
        """
        start_time = time.time()
        
        try:
            # Check if the image exists
            if not os.path.exists(image_path):
                logger.warning(f"Image not found: {image_path}")
                return None
            
            # Open the image
            try:
                # Using PIL for basic processing
                image = Image.open(image_path).convert('RGB')
                
                # Basic image properties
                width, height = image.size
                aspect_ratio = width / height
            except Exception as e:
                logger.error(f"Failed to open image {image_path}: {e}")
                return None
            
            # Initialize features dictionary
            features = {
                'basic': {
                    'width': width,
                    'height': height,
                    'aspect_ratio': aspect_ratio,
                    'orientation': 'landscape' if width > height else 'portrait' if height > width else 'square'
                },
                'tags': set()  # Use a set to avoid duplicates
            }
            
            # Add orientation tag
            features['tags'].add(features['basic']['orientation'])
            
            # Extract color features
            color_features = self._extract_color_features(image)
            features['color'] = color_features
            
            # Add color tags
            for color_name in color_features['dominant_colors']:
                features['tags'].add(f"color:{color_name}")
            
            # Add brightness tag
            features['tags'].add(f"brightness:{color_features['brightness_category']}")
            
            # Extract composition features
            composition_features = self._extract_composition_features(image)
            features['composition'] = composition_features
            
            # Add composition tags
            if composition_features.get('high_contrast', False):
                features['tags'].add('high_contrast')
            
            if composition_features.get('rule_of_thirds', False):
                features['tags'].add('rule_of_thirds')
            
            # Extract EXIF data if available
            exif_features = self._extract_exif_features(image_path, image)
            if exif_features:
                features['exif'] = exif_features
                
                # Add camera model tag if available
                if 'camera_model' in exif_features:
                    features['tags'].add(f"camera:{exif_features['camera_model']}")
                
                # Add lens tag if available
                if 'lens' in exif_features:
                    features['tags'].add(f"lens:{exif_features['lens']}")
            
            # ML-based feature extraction
            if self.use_ml_features:
                # Extract objects using object detection
                if 'object_detector' in self.ml_models:
                    objects = self._detect_objects(image_path)
                    if objects:
                        features['objects'] = objects
                        
                        # Add object tags
                        for obj in objects:
                            features['tags'].add(f"contains:{obj['label']}")
                
                # Detect faces
                if 'face_detector' in self.ml_models:
                    faces = self._detect_faces(image_path)
                    if faces:
                        features['faces'] = faces
                        features['tags'].add(f"contains:face")
                        
                        # Add face count tag
                        face_count = len(faces)
                        if face_count == 1:
                            features['tags'].add("single_person")
                        elif 2 <= face_count <= 4:
                            features['tags'].add("small_group")
                        elif face_count > 4:
                            features['tags'].add("large_group")
            
            # Convert tags set to list for serialization
            features['tags'] = list(features['tags'])
            
            elapsed_time = time.time() - start_time
            logger.info(f"Features extracted for {image_path} in {elapsed_time:.2f} seconds. {len(features['tags'])} tags generated.")
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features from {image_path}: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _extract_color_features(self, image):
        """
        Extract color-related features from an image
        
        Args:
            image (PIL.Image): The input image
            
        Returns:
            dict: Color features
        """
        try:
            # Resize for faster processing
            img_small = image.resize((100, 100))
            pixels = list(img_small.getdata())
            
            # Calculate average RGB
            avg_r = sum(p[0] for p in pixels) / len(pixels)
            avg_g = sum(p[1] for p in pixels) / len(pixels)
            avg_b = sum(p[2] for p in pixels) / len(pixels)
            
            # Calculate average brightness (0-1 scale)
            avg_brightness = (avg_r + avg_g + avg_b) / (3 * 255)
            
            # Categorize brightness
            if avg_brightness < 0.3:
                brightness_category = 'dark'
            elif avg_brightness < 0.7:
                brightness_category = 'medium'
            else:
                brightness_category = 'bright'
            
            # Extract dominant colors
            dominant_colors = self._extract_dominant_colors(pixels, n=5)
            
            # Calculate color contrast
            # For simplicity, we'll use standard deviation of pixel values
            r_values = [p[0] for p in pixels]
            g_values = [p[1] for p in pixels]
            b_values = [p[2] for p in pixels]
            
            r_std = np.std(r_values) / 255
            g_std = np.std(g_values) / 255
            b_std = np.std(b_values) / 255
            
            color_contrast = (r_std + g_std + b_std) / 3
            
            return {
                'avg_rgb': [float(avg_r), float(avg_g), float(avg_b)],
                'avg_brightness': float(avg_brightness),
                'brightness_category': brightness_category,
                'color_contrast': float(color_contrast),
                'dominant_colors': [c[0] for c in dominant_colors],
                'color_hex': '#%02x%02x%02x' % (int(avg_r), int(avg_g), int(avg_b))
            }
            
        except Exception as e:
            logger.error(f"Error extracting color features: {e}")
            return {
                'avg_rgb': [0, 0, 0],
                'avg_brightness': 0,
                'brightness_category': 'unknown',
                'color_contrast': 0,
                'dominant_colors': [],
                'color_hex': '#000000'
            }
    
    def _extract_dominant_colors(self, pixels, n=5):
        """
        Extract dominant colors from image pixels
        
        Args:
            pixels: List of RGB tuples
            n: Number of dominant colors to extract
            
        Returns:
            list: List of (color_name, count) tuples
        """
        # Define color ranges with names
        color_names = {
            'red': ((340, 360), (0, 20), (50, 100), (50, 100)),  # (hue range, saturation range, value range)
            'orange': ((20, 40), (50, 100), (50, 100)),
            'yellow': ((40, 70), (50, 100), (50, 100)),
            'green': ((70, 160), (30, 100), (30, 100)),
            'teal': ((160, 200), (30, 100), (30, 100)),
            'blue': ((200, 250), (30, 100), (30, 100)),
            'purple': ((250, 290), (30, 100), (30, 100)),
            'pink': ((290, 340), (30, 100), (30, 100)),
            'black': ((0, 360), (0, 100), (0, 15)),
            'gray': ((0, 360), (0, 15), (15, 85)),
            'white': ((0, 360), (0, 15), (85, 100))
        }
        
        # Function to get color name from RGB
        def get_color_name(r, g, b):
            # Convert RGB to HSV
            r, g, b = r/255.0, g/255.0, b/255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            h = h * 360  # Convert to 0-360 range
            s = s * 100  # Convert to 0-100 range
            v = v * 100  # Convert to 0-100 range
            
            # Check each color range
            for name, ranges in color_names.items():
                if len(ranges) == 3:
                    h_range, s_range, v_range = ranges
                    # Handle red hue which wraps around
                    if name == 'red' and (h >= h_range[0] or h <= h_range[1]):
                        if s_range[0] <= s <= s_range[1] and v_range[0] <= v <= v_range[1]:
                            return name
                    # Normal case
                    elif h_range[0] <= h <= h_range[1] and s_range[0] <= s <= s_range[1] and v_range[0] <= v <= v_range[1]:
                        return name
                # Special case for red which crosses the 0/360 boundary
                elif len(ranges) == 4:
                    h_range1, h_range2, s_range, v_range = ranges
                    if ((h_range1[0] <= h <= h_range1[1]) or (h_range2[0] <= h <= h_range2[1])) and s_range[0] <= s <= s_range[1] and v_range[0] <= v <= v_range[1]:
                        return name
            
            # Default if no match
            return 'other'
        
        # Get color names for each pixel
        color_names_list = [get_color_name(p[0], p[1], p[2]) for p in pixels]
        
        # Count occurrences
        color_counts = Counter(color_names_list)
        
        # Return top n colors
        return color_counts.most_common(n)
    
    def _extract_composition_features(self, image):
        """
        Extract composition-related features from an image
        
        Args:
            image (PIL.Image): The input image
            
        Returns:
            dict: Composition features
        """
        try:
            width, height = image.size
            
            # Resize for faster processing
            img_small = image.resize((100, 100))
            img_array = np.array(img_small)
            
            # Calculate edges using simple gradient
            if OPENCV_AVAILABLE:
                # Convert to grayscale
                gray = cv2.cvtColor(np.array(img_small), cv2.COLOR_RGB2GRAY)
                
                # Calculate edges with Canny edge detector
                edges = cv2.Canny(gray, 100, 200)
                edge_percentage = np.count_nonzero(edges) / (edges.shape[0] * edges.shape[1])
                
                # Check rule of thirds - look for strong lines/edges at third points
                thirds_h = [height // 3, 2 * height // 3]
                thirds_v = [width // 3, 2 * width // 3]
                
                # Simple rule of thirds detection (more advanced versions would be possible)
                # Check for more edges around third lines
                third_regions = np.zeros_like(edges)
                third_region_size = min(width, height) // 15  # Region around the thirds lines
                
                for h in thirds_h:
                    third_regions[max(0, h - third_region_size):min(edges.shape[0], h + third_region_size), :] = 1
                
                for v in thirds_v:
                    third_regions[:, max(0, v - third_region_size):min(edges.shape[1], v + third_region_size)] = 1
                
                # Calculate edge density in thirds regions vs whole image
                thirds_edges = np.logical_and(edges > 0, third_regions > 0)
                thirds_area = np.sum(third_regions)
                thirds_edge_density = np.sum(thirds_edges) / thirds_area if thirds_area > 0 else 0
                
                # Compare to overall edge density
                overall_edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
                
                # Determine if rule of thirds is being used
                rule_of_thirds = thirds_edge_density > overall_edge_density * 1.2
                
            else:
                # Simplified calculation without OpenCV
                # Convert to grayscale and calculate gradient magnitude
                grayscale = np.array(img_small.convert('L'))
                gradient_x = np.abs(np.diff(grayscale, axis=1, prepend=0))
                gradient_y = np.abs(np.diff(grayscale, axis=0, prepend=0))
                gradient_mag = np.sqrt(gradient_x**2 + gradient_y**2)
                
                # Use a threshold to determine edges
                edge_threshold = np.percentile(gradient_mag, 90)  # Adjust as needed
                edges = gradient_mag > edge_threshold
                edge_percentage = np.mean(edges)
                
                # Simplified rule of thirds detection
                rule_of_thirds = False
            
            # Calculate symmetry
            # Horizontal symmetry
            left_half = img_array[:, :img_array.shape[1]//2]
            right_half = np.fliplr(img_array[:, img_array.shape[1]//2:])
            
            # Handle different sizes if odd width
            min_width = min(left_half.shape[1], right_half.shape[1])
            h_symmetry_diff = np.mean(np.abs(left_half[:, :min_width] - right_half[:, :min_width]))
            h_symmetry = 1 - h_symmetry_diff / 255
            
            # Vertical symmetry
            top_half = img_array[:img_array.shape[0]//2, :]
            bottom_half = np.flipud(img_array[img_array.shape[0]//2:, :])
            
            # Handle different sizes if odd height
            min_height = min(top_half.shape[0], bottom_half.shape[0])
            v_symmetry_diff = np.mean(np.abs(top_half[:min_height, :] - bottom_half[:min_height, :]))
            v_symmetry = 1 - v_symmetry_diff / 255
            
            return {
                'edge_percentage': float(edge_percentage),
                'high_contrast': edge_percentage > 0.1,  # Threshold can be adjusted
                'rule_of_thirds': bool(rule_of_thirds),
                'horizontal_symmetry': float(h_symmetry),
                'vertical_symmetry': float(v_symmetry),
                'overall_symmetry': float((h_symmetry + v_symmetry) / 2)
            }
            
        except Exception as e:
            logger.error(f"Error extracting composition features: {e}")
            logger.error(traceback.format_exc())
            return {
                'edge_percentage': 0.0,
                'high_contrast': False,
                'rule_of_thirds': False,
                'horizontal_symmetry': 0.0,
                'vertical_symmetry': 0.0,
                'overall_symmetry': 0.0
            }
    
    def _extract_exif_features(self, image_path, image):
        """
        Extract EXIF metadata from an image
        
        Args:
            image_path (str): Path to the image
            image (PIL.Image): The image object
            
        Returns:
            dict: EXIF features or None if not available
        """
        try:
            # Check if image has EXIF data
            exif_data = image._getexif()
            if not exif_data:
                return None
            
            # EXIF tags mapping
            TAGS = {
                271: 'camera_make',
                272: 'camera_model',
                306: 'datetime',
                33434: 'exposure_time',
                33437: 'aperture',
                34855: 'iso',
                37386: 'focal_length',
                42036: 'lens'
            }
            
            # Extract relevant EXIF data
            exif_features = {}
            for tag, value in exif_data.items():
                if tag in TAGS:
                    tag_name = TAGS[tag]
                    
                    # Process specific tags
                    if tag_name == 'exposure_time':
                        # Convert to readable format (e.g., "1/250")
                        if value < 1:
                            exif_features[tag_name] = f"1/{int(1/value)}"
                        else:
                            exif_features[tag_name] = str(value)
                    elif tag_name == 'aperture':
                        # Convert to f-number
                        exif_features[tag_name] = f"f/{value}"
                    elif tag_name == 'focal_length':
                        # Extract numerical value
                        if isinstance(value, tuple) and len(value) == 2:
                            exif_features[tag_name] = f"{value[0]/value[1]}mm"
                        else:
                            exif_features[tag_name] = f"{value}mm"
                    else:
                        # General case
                        exif_features[tag_name] = str(value)
            
            return exif_features
            
        except Exception as e:
            logger.debug(f"Error extracting EXIF data: {e}")
            return None
    
    def _detect_objects(self, image_path):
        """
        Detect objects in the image using TensorFlow model
        
        Args:
            image_path (str): Path to the image
            
        Returns:
            list: Detected objects with labels and confidence scores
        """
        if not TENSORFLOW_AVAILABLE or 'object_detector' not in self.ml_models:
            return None
            
        try:
            # Load image for TensorFlow
            img = tf.io.read_file(image_path)
            img = tf.image.decode_image(img, channels=3)
            img = tf.image.convert_image_dtype(img, tf.uint8)
            
            # Get image dimensions
            img_height, img_width = img.shape[0], img.shape[1]
            
            # Prepare input for model
            input_img = tf.image.resize(img, [300, 300])
            input_tensor = tf.expand_dims(input_img, 0)
            
            # Run inference
            detector = self.ml_models['object_detector']
            detections = detector(input_tensor)
            
            # Process results
            detected_objects = []
            
            # Extract detection results
            boxes = detections['detection_boxes'][0].numpy()
            classes = detections['detection_classes'][0].numpy().astype(np.int32)
            scores = detections['detection_scores'][0].numpy()
            
            # Class ID to name mapping (COCO dataset)
            # This is a simplified subset - a real implementation would include all COCO classes
            class_names = {
                1: 'person', 2: 'bicycle', 3: 'car', 4: 'motorcycle', 5: 'airplane',
                6: 'bus', 7: 'train', 8: 'truck', 9: 'boat', 10: 'traffic light',
                11: 'fire hydrant', 13: 'stop sign', 14: 'parking meter', 15: 'bench',
                16: 'bird', 17: 'cat', 18: 'dog', 19: 'horse', 20: 'sheep',
                21: 'cow', 22: 'elephant', 23: 'bear', 24: 'zebra', 25: 'giraffe',
                27: 'backpack', 28: 'umbrella', 31: 'handbag', 32: 'tie',
                33: 'suitcase', 34: 'frisbee', 35: 'skis', 36: 'snowboard',
                37: 'sports ball', 38: 'kite', 39: 'baseball bat', 40: 'baseball glove',
                41: 'skateboard', 42: 'surfboard', 43: 'tennis racket', 44: 'bottle',
                46: 'wine glass', 47: 'cup', 48: 'fork', 49: 'knife', 50: 'spoon',
                51: 'bowl', 52: 'banana', 53: 'apple', 54: 'sandwich', 55: 'orange',
                56: 'broccoli', 57: 'carrot', 58: 'hot dog', 59: 'pizza', 60: 'donut',
                61: 'cake', 62: 'chair', 63: 'couch', 64: 'potted plant', 65: 'bed',
                67: 'dining table', 70: 'toilet', 72: 'tv', 73: 'laptop', 74: 'mouse',
                75: 'remote', 76: 'keyboard', 77: 'cell phone', 78: 'microwave',
                79: 'oven', 80: 'toaster', 81: 'sink', 82: 'refrigerator',
                84: 'book', 85: 'clock', 86: 'vase', 87: 'scissors', 88: 'teddy bear',
                89: 'hair drier', 90: 'toothbrush'
            }
            
            # Filter detections with good confidence
            min_score_threshold = 0.4
            for i in range(min(100, boxes.shape[0])):
                if scores[i] >= min_score_threshold:
                    class_id = classes[i]
                    class_name = class_names.get(class_id, f"unknown_class_{class_id}")
                    
                    # Convert box to pixel coordinates
                    ymin, xmin, ymax, xmax = boxes[i]
                    x = int(xmin * img_width)
                    y = int(ymin * img_height)
                    w = int((xmax - xmin) * img_width)
                    h = int((ymax - ymin) * img_height)
                    
                    detected_objects.append({
                        'label': class_name,
                        'confidence': float(scores[i]),
                        'box': [x, y, w, h]
                    })
            
            return detected_objects
            
        except Exception as e:
            logger.error(f"Error detecting objects: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _detect_faces(self, image_path):
        """
        Detect faces in the image using OpenCV
        
        Args:
            image_path (str): Path to the image
            
        Returns:
            list: Detected faces with positions
        """
        if not OPENCV_AVAILABLE or 'face_detector' not in self.ml_models:
            return None
            
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                logger.warning(f"Could not load image for face detection: {image_path}")
                return None
                
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            face_cascade = self.ml_models['face_detector']
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Format results
            face_list = []
            for (x, y, w, h) in faces:
                face_list.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h)
                })
            
            return face_list
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            logger.error(traceback.format_exc())
            return None

# Batch feature extraction for efficiency
def batch_extract_features(image_paths, use_ml_features=True, batch_size=10):
    """
    Extract features for multiple images in batches
    
    Args:
        image_paths (list): List of image paths
        use_ml_features (bool): Whether to use ML-based features
        batch_size (int): Number of images to process in each batch
        
    Returns:
        dict: Dictionary mapping paths to features
    """
    extractor = ImageFeatureExtractor(use_ml_features=use_ml_features)
    results = {}
    
    for i in range(0, len(image_paths), batch_size):
        batch = image_paths[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{math.ceil(len(image_paths)/batch_size)} ({len(batch)} images)")
        
        for path in batch:
            features = extractor.extract_features(path)
            if features:
                results[path] = features
    
    return results