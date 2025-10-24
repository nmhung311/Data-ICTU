"""
Image OCR extraction for Raw2MD Agent.

Uses PaddleOCR GPU-accelerated engine for Vietnamese text extraction from images.
"""

import logging
from typing import Optional, Dict, Any, List

from .base import BaseExtractor, ExtractionError, CorruptedFileError

logger = logging.getLogger(__name__)

# Import PIL with error handling
try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
    logger.debug("PIL successfully imported")
except ImportError as e:
    PIL_AVAILABLE = False
    logger.error(f"PIL not available: {e}. Some functionality will be limited.")
    logger.info("To enable full functionality, install Pillow: pip install Pillow")
except Exception as e:
    PIL_AVAILABLE = False
    logger.error(f"Unexpected error importing PIL: {e}")
    logger.info("To enable full functionality, install Pillow: pip install Pillow")

# Import numpy with error handling
try:
    import numpy as np
    NUMPY_AVAILABLE = True
    logger.debug("NumPy successfully imported")
except ImportError as e:
    NUMPY_AVAILABLE = False
    logger.error(f"NumPy not available: {e}. Some functionality will be limited.")
    logger.info("To enable full functionality, install NumPy: pip install numpy")
except Exception as e:
    NUMPY_AVAILABLE = False
    logger.error(f"Unexpected error importing NumPy: {e}")
    logger.info("To enable full functionality, install NumPy: pip install numpy")

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR not available. Image OCR extraction will not work.")


class ImageExtractor(BaseExtractor):
    """
    Image OCR extractor using PaddleOCR GPU acceleration.
    
    Features:
    - PaddleOCR GPU-accelerated OCR engine
    - Preprocessing: grayscale conversion, contrast enhancement
    - Language support: Vietnamese ('vi'), English ('en'), multilingual ('latin')
    - Output formatting: preserve spatial text layout
    - Supported formats: JPEG, PNG, TIFF, BMP, WEBP
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Image extractor.
        
        Args:
            path: Path to image file
            config: Optional configuration dictionary
        """
        super().__init__(path, config)
        
        if not PADDLEOCR_AVAILABLE:
            raise ExtractionError("PaddleOCR library not available", str(self.path))
        
        # OCR configuration
        self.use_gpu = config.get('use_gpu', True) if config else True
        self.lang = config.get('lang', 'vi') if config else 'vi'
        self.confidence_threshold = config.get('confidence_threshold', 0.6) if config else 0.6
        self.enable_preprocessing = config.get('enable_preprocessing', True) if config else True
        
        # Initialize OCR engine
        self.ocr_engine = None
        self._initialize_ocr()
    
    def _initialize_ocr(self) -> None:
        """Initialize PaddleOCR engine."""
        try:
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=self.use_gpu,
                show_log=False,
                use_space_char=True
            )
            logger.debug(f"PaddleOCR initialized successfully (GPU: {self.use_gpu}, Lang: {self.lang})")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise ExtractionError(f"Failed to initialize OCR engine: {e}", str(self.path), e)
    
    def extract(self) -> str:
        """
        Extract text from image using OCR.
        
        Returns:
            Extracted text content
            
        Raises:
            ExtractionError: If extraction fails
            CorruptedFileError: If image is corrupted
        """
        try:
            # Load and preprocess image
            image = self._load_and_preprocess_image()
            
            # Perform OCR
            if self.ocr_engine is None:
                raise ExtractionError("OCR engine not initialized", str(self.path))
                
            ocr_result = self.ocr_engine.ocr(image, cls=True)
            
            if not ocr_result or not ocr_result[0]:
                raise ExtractionError("No text detected in image", str(self.path))
            
            # Extract and format text
            extracted_text = self._format_ocr_result(ocr_result[0])
            
            if not extracted_text.strip():
                raise ExtractionError("No readable text found in image", str(self.path))
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters from image")
            return extracted_text
            
        except Exception as e:
            if "corrupted" in str(e).lower() or "cannot identify" in str(e).lower():
                raise CorruptedFileError(f"Image file appears to be corrupted: {e}", str(self.path), e)
            raise ExtractionError(f"Failed to extract text from image: {e}", str(self.path), e)
    
    def _load_and_preprocess_image(self):
        """
        Load and preprocess image for OCR.
        
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Load image
            image = Image.open(self.path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply preprocessing if enabled
            if self.enable_preprocessing:
                image = self._preprocess_image(image)
            
            # Convert to numpy array
            img_array = np.array(image)
            
            return img_array
            
        except Exception as e:
            raise ExtractionError(f"Failed to load image: {e}", str(self.path), e)
    
    def _preprocess_image(self, image: 'Image.Image') -> 'Image.Image':
        """
        Apply image preprocessing to improve OCR accuracy.
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image
        """
        try:
            # Convert to grayscale for better OCR
            if image.mode == 'RGB':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Convert back to RGB for PaddleOCR
            image = image.convert('RGB')
            
            return image
            
        except Exception as e:
            logger.warning(f"Error in image preprocessing: {e}")
            return image
    
    def _format_ocr_result(self, ocr_result: List) -> str:
        """
        Format OCR result into readable text.
        
        Args:
            ocr_result: Raw OCR result from PaddleOCR
            
        Returns:
            Formatted text content
        """
        text_lines = []
        
        # Sort lines by vertical position (top to bottom)
        sorted_lines = self._sort_lines_by_position(ocr_result)
        
        for line_data in sorted_lines:
            text = line_data['text']
            confidence = line_data['confidence']
            
            # Filter by confidence threshold
            if confidence >= self.confidence_threshold:
                text_lines.append(text)
            else:
                logger.debug(f"Skipping low confidence text: '{text}' (confidence: {confidence:.2f})")
        
        return '\n'.join(text_lines)
    
    def _sort_lines_by_position(self, ocr_result: List) -> List[Dict[str, Any]]:
        """
        Sort OCR lines by their vertical position (top to bottom).
        
        Args:
            ocr_result: Raw OCR result
            
        Returns:
            List of sorted line data
        """
        line_data = []
        
        for line in ocr_result:
            if len(line) >= 2:
                bbox = line[0]
                text = line[1][0]
                confidence = line[1][1]
                
                # Calculate average Y position
                y_pos = sum(point[1] for point in bbox) / len(bbox)
                
                line_data.append({
                    'text': text,
                    'confidence': confidence,
                    'y_position': y_pos,
                    'bbox': bbox
                })
        
        # Sort by Y position
        line_data.sort(key=lambda x: x['y_position'])
        
        return line_data
    
    def get_image_info(self) -> Dict[str, Any]:
        """
        Get basic image information.
        
        Returns:
            Dictionary with image information
        """
        try:
            with Image.open(self.path) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                }
        except Exception as e:
            logger.warning(f"Error getting image info: {e}")
            return {}
    
    def extract_with_confidence(self) -> List[Dict[str, Any]]:
        """
        Extract text with confidence scores and bounding boxes.
        
        Returns:
            List of text data with confidence and position info
        """
        try:
            image = self._load_and_preprocess_image()
            
            if self.ocr_engine is None:
                return []
                
            ocr_result = self.ocr_engine.ocr(image, cls=True)
            
            if not ocr_result or not ocr_result[0]:
                return []
            
            return self._sort_lines_by_position(ocr_result[0])
            
        except Exception as e:
            logger.warning(f"Error extracting with confidence: {e}")
            return []
    
    def is_text_image(self) -> bool:
        """
        Check if image likely contains text.
        
        Returns:
            True if image appears to contain text
        """
        try:
            # Quick OCR check on a smaller version
            image = Image.open(self.path)
            
            # Resize to smaller size for quick check
            image.thumbnail((400, 400))
            img_array = np.array(image)
            
            if self.ocr_engine is None:
                return False
                
            ocr_result = self.ocr_engine.ocr(img_array, cls=True)
            
            if ocr_result and ocr_result[0]:
                # Check if any text has reasonable confidence
                for line in ocr_result[0]:
                    if len(line) >= 2 and line[1][1] > 0.5:
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking if image contains text: {e}")
            return False
