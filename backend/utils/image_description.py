from PIL import Image
import logging
import os
import time

logger = logging.getLogger('image-similarity')

#check if transformers is available
TRANSFORMERS_AVAILABLE = False
try:
    from transformers import AutoProcessor, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
    logger.info("transformers library available for image descriptions")
except ImportError:
    logger.warning("transformers library not available, falling back to basic descriptions")

class ImageDescriptionGenerator:
    def __init__(self, model_name="Salesforce/blip-image-captioning-base"):
        """
        intit the image description generator with a vision-language model.

        Args:
            model_name (str): name of model to use, default is BLIP.
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers library not available")
        
        logger.info(f"initialising ImageDescriptionGenerator with model: {model_name}")
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"using device {self.device}")


        #lod the model and processor
        try:
            self.processor = AutoProcessor.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"error loading model: {e}")
            raise
    
    def generate_description(self, image_path, max_length=50):
        """
        generate a description for the given image

        Args:
            image_path (str): path to image
            max_length (int): maximum length of the description

        Returns:
            str: a human-readable description of the image
        """
        try:
            start_time = time.time()
            #load the image
            if not os.path.exists(image_path):
                logger.warning(f"image not found: {image_path}")
                return "image not found"
            
            image = Image.open(image_path).convert('RGB')

            #generate description            
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=4,
                    early_stopping=True
                )
            #decode output
            description = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            elapsed_time = time.time() - start_time
            logger.info(f"description generated in {elapsed_time:.2f} seconds: {description}")
            return description
        
        except Exception as e:
            logger.error(f"error generating description for {image_path}: {e}")
            return "error generating description"
    
# Fallback description generator using basic image properties
def generate_basic_description(image_path):
    """
    Generate a basic description using image properties when ML model is not available.
    
    Args:
        image_path (str): Path to the image
        
    Returns:
        str: A basic description of the image
    """
    try:
        if not os.path.exists(image_path):
            return "Image not found"
            
        image = Image.open(image_path)
        
        # Get basic image properties
        width, height = image.size
        format_type = image.format or "Unknown"
        mode = image.mode
        
        # Extract context from filename
        filename = os.path.basename(image_path)
        name_without_ext = os.path.splitext(filename)[0]
        words = name_without_ext.replace('_', ' ').replace('-', ' ').split()
        
        # Try to determine what the image might be of based on filename
        context = ' '.join(words)
        
        # Get color information
        try:
            # Resize for faster processing
            small_img = image.resize((100, 100))
            
            # Convert to RGB if not already
            if small_img.mode != 'RGB':
                small_img = small_img.convert('RGB')
                
            # Calculate average color
            avg_color = [0, 0, 0]
            pixel_count = 0
            
            for x in range(small_img.width):
                for y in range(small_img.height):
                    r, g, b = small_img.getpixel((x, y))
                    avg_color[0] += r
                    avg_color[1] += g
                    avg_color[2] += b
                    pixel_count += 1
            
            avg_color = [c // pixel_count for c in avg_color]
            
            # Determine dominant color
            r, g, b = avg_color
            
            # Simple color determination
            colors = []
            if r > 200 and g > 200 and b > 200:
                colors.append("white")
            elif r < 50 and g < 50 and b < 50:
                colors.append("black")
            else:
                if r > g + 50 and r > b + 50:
                    colors.append("red")
                if g > r + 50 and g > b + 50:
                    colors.append("green")
                if b > r + 50 and b > g + 50:
                    colors.append("blue")
                if r > 200 and g > 150 and b < 100:
                    colors.append("yellow")
                if r > 200 and g < 100 and b > 150:
                    colors.append("purple")
                if r > 200 and g > 100 and b < 100:
                    colors.append("orange")
                if r > 150 and g > 150 and b > 150:
                    colors.append("gray")
            
            color_description = " and ".join(colors) if colors else "multicolored"
            
        except Exception as color_error:
            logger.warning(f"Error analyzing colors: {color_error}")
            color_description = "varied colors"
        
        # Create basic description
        if context:
            description = f"{color_description} image of {context} ({format_type}, {width}x{height}px)"
        else:
            description = f"{color_description} {format_type} image, {width}x{height}px"
        
        return description
        
    except Exception as e:
        logger.error(f"Error generating basic description for {image_path}: {e}")
        return "Image file (no description available)"

# Get the most appropriate description generator based on available libraries
def get_description_generator(use_ml=True):
    """
    Get the most appropriate description generator based on available libraries.
    
    Args:
        use_ml (bool): Whether to try using ML-based generator first
        
    Returns:
        function or object: A description generator function or object
    """
    if use_ml and TRANSFORMERS_AVAILABLE:
        try:
            return ImageDescriptionGenerator()
        except Exception as e:
            logger.warning(f"Failed to initialize ML description generator: {e}")
    
    # Return the basic description function as fallback
    return generate_basic_description