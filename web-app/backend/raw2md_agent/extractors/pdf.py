"""
PDF text extraction with OCR support for Raw2MD Agent.

Uses PyMuPDF for text-based PDFs and PaddleOCR GPU for scanned pages.
"""

import logging
from typing import Optional, Dict, Any, List
import io

from .base import BaseExtractor, ExtractionError, CorruptedFileError

logger = logging.getLogger(__name__)

# Import PIL with error handling
try:
    from PIL import Image
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
    import numpy  # type: ignore
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

# Import PyMuPDF (fitz) with error handling
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    logger.debug("PyMuPDF successfully imported")
except ImportError as e:
    PYMUPDF_AVAILABLE = False
    logger.error(f"PyMuPDF not available: {e}. PDF processing will not work.")
    logger.info("To enable PDF processing, install PyMuPDF: pip install PyMuPDF")
except Exception as e:
    PYMUPDF_AVAILABLE = False
    logger.error(f"Unexpected error importing PyMuPDF: {e}")
    logger.info("To enable PDF processing, install PyMuPDF: pip install PyMuPDF")

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
    logger.debug("PaddleOCR successfully imported")
except ImportError as e:
    PADDLEOCR_AVAILABLE = False
    logger.warning(f"PaddleOCR not available: {e}. OCR functionality will be limited.")
    logger.info("To enable OCR functionality, install PaddleOCR: pip install paddleocr paddlepaddle")
except Exception as e:
    PADDLEOCR_AVAILABLE = False
    logger.error(f"Unexpected error importing PaddleOCR: {e}")
    logger.info("To enable OCR functionality, install PaddleOCR: pip install paddleocr paddlepaddle")

# Fallback to pytesseract
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
    logger.debug("pytesseract successfully imported")
except ImportError as e:
    PYTESSERACT_AVAILABLE = False
    logger.warning(f"pytesseract not available: {e}")
except Exception as e:
    PYTESSERACT_AVAILABLE = False
    logger.error(f"Unexpected error importing pytesseract: {e}")

# Import optimized Tesseract OCR
try:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    # from optimized_tesseract_ocr import OptimizedTesseractOCR  # Removed - file no longer exists
    OPTIMIZED_TESSERACT_AVAILABLE = False
    logger.debug("Optimized Tesseract OCR not available - file removed")
except ImportError as e:
    OPTIMIZED_TESSERACT_AVAILABLE = False
    logger.warning(f"Optimized Tesseract OCR not available: {e}")
except Exception as e:
    OPTIMIZED_TESSERACT_AVAILABLE = False
    logger.error(f"Unexpected error importing Optimized Tesseract OCR: {e}")


class PDFExtractor(BaseExtractor):
    """
    PDF text extractor with automatic OCR fallback for scanned pages.
    
    Features:
    - PyMuPDF for text-based PDF extraction
    - Automatic scanned page detection
    - PaddleOCR GPU integration for scanned pages
    - Confidence threshold filtering
    - Bounding box text ordering
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize PDF extractor.
        
        Args:
            path: Path to PDF file
            config: Configuration dictionary with OCR settings
        """
        super().__init__(path, config)
        
        # OCR configuration - chuẩn hóa ngôn ngữ cho từng OCR
        self.use_gpu = config.get('use_gpu', True) if config else True
        self.lang_tesseract = config.get('lang', 'vie+eng') if config else 'vie+eng'  # Tesseract hỗ trợ multi
        self.lang_paddle = 'vi'  # PaddleOCR dùng 'vi'
        self.confidence_threshold = config.get('confidence_threshold', 0.5) if config else 0.5
        
        # Initialize OCR engines if available
        self.ocr_engine = None
        self.optimized_tesseract = None
        
        # Optimized Tesseract not available - file removed
        self.optimized_tesseract = None
        logger.debug("Optimized Tesseract OCR not available - using fallback OCR engines")
        
        # Fallback to PaddleOCR
        if PADDLEOCR_AVAILABLE and not self.optimized_tesseract:
            try:
                self.ocr_engine = PaddleOCR(
                    use_gpu=self.use_gpu,
                    lang=self.lang_paddle,
                    use_angle_cls=True
                )
                logger.debug("PaddleOCR initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize PaddleOCR: {e}")
                logger.info("Make sure you have installed: pip install paddleocr paddlepaddle")
                self.ocr_engine = None
        else:
            logger.info("PaddleOCR not available. Install with: pip install paddleocr paddlepaddle")
    
    def extract(self) -> str:
        """
        Extract text from PDF file.
        
        Returns:
            Extracted text content
            
        Raises:
            ExtractionError: If extraction fails
            CorruptedFileError: If PDF is corrupted
        """
        if not PYMUPDF_AVAILABLE:
            raise ExtractionError("PyMuPDF not available. Cannot process PDF files.", str(self.path))
            
        try:
            # Open PDF document
            doc = fitz.open(str(self.path))
            logger.debug(f"Opened PDF with {len(doc)} pages")
            
            extracted_texts = []
            
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    
                    # First try to extract text directly
                    text = page.get_text()
                    
                    # Ensure text is a string
                    if isinstance(text, (list, dict)):
                        text = str(text)
                    
                    # Check if page has sufficient text content
                    if self._page_has_textlayer(page):
                        logger.debug(f"Page {page_num + 1}: Using direct text extraction")
                        extracted_texts.append(text)
                    else:
                        # Page appears to be scanned, use OCR
                        logger.debug(f"Page {page_num + 1}: Using OCR extraction")
                        ocr_text = self._extract_with_ocr(page)
                        extracted_texts.append(ocr_text)
                        
                except Exception as e:
                    logger.warning(f"Error processing page {page_num + 1}: {e}")
                    extracted_texts.append("")  # Add empty string for failed page
            
            doc.close()
            
            # Combine all page texts
            full_text = "\n\n".join(extracted_texts)
            
            if not full_text.strip():
                raise ExtractionError("No text content found in PDF", str(self.path))
            
            logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
            return full_text
            
        except fitz.FileDataError as e:
            raise CorruptedFileError(f"PDF file appears to be corrupted: {e}", str(self.path), e)
        except Exception as e:
            raise ExtractionError(f"Failed to extract text from PDF: {e}", str(self.path), e)
    
    def _page_has_textlayer(self, page, min_chars: int = 40, min_blocks: int = 1) -> bool:
        """
        Check if page has sufficient text layer using PyMuPDF textpage.
        
        Args:
            page: PyMuPDF page object
            min_chars: Minimum character threshold
            min_blocks: Minimum text blocks threshold
            
        Returns:
            True if page has sufficient text layer, False if likely scanned
        """
        try:
            tp = page.get_textpage()
            # blocks: (x0,y0,x1,y1,"lines", block_no, block_type)
            blocks = tp.extractBLOCKS()
            text = page.get_text("text") or ""
            if len(text.strip()) >= min_chars and sum(1 for b in blocks if len(b) >= 6 and b[6] == 0) >= min_blocks:
                return True
            return False
        except Exception:
            # fallback to simple text check
            txt = page.get_text() or ""
            return len((txt or "").strip()) >= min_chars
    
    def _page_to_image_bytes(self, page, max_edge_px: int = 2200) -> Optional[bytes]:
        """
        Render page to image bytes with safe RAM usage and DPI scaling.
        
        Args:
            page: PyMuPDF page object
            max_edge_px: Maximum edge length in pixels
            
        Returns:
            Image bytes or None if failed
        """
        try:
            # Tính scale sao cho cạnh dài ~ max_edge_px
            rect = page.rect
            long_edge = max(rect.width, rect.height)
            # 72 dpi gốc -> scale ~ (max_edge / long_edge)
            scale = max(2.0, min(4.0, (max_edge_px / long_edge) * (72.0 / 72.0)))
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")
        except Exception as e:
            logger.warning(f"Failed to rasterize page: {e}")
            return None
    
    def _extract_with_ocr(self, page) -> str:
        """
        Extract text from page using OCR engines.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            Extracted text string
        """
        # Optimized Tesseract not available - file removed
        # Fallback to PaddleOCR
        if self.ocr_engine and NUMPY_AVAILABLE:
            try:
                img_bytes = self._page_to_image_bytes(page)
                if img_bytes and PIL_AVAILABLE:
                    image = Image.open(io.BytesIO(img_bytes))
                    import numpy as np
                    arr = np.array(image)
                    result = self.ocr_engine.ocr(arr, cls=True)
                    if result and result[0]:
                        # sort theo (y, x)
                        lines = []
                        for item in result[0]:
                            if len(item) >= 2:
                                box, txt = item[0], item[1][0]
                                y = min(p[1] for p in box)
                                x = min(p[0] for p in box)
                                lines.append((y, x, txt))
                        lines.sort(key=lambda t: (t[0], t[1]))
                        text = "\n".join(t[2] for t in lines if t[2])
                        if text.strip():
                            logger.debug(f"PaddleOCR extracted {len(text)} characters")
                            return text
            except Exception as e:
                logger.warning(f"PaddleOCR extraction failed: {e}")
        
        # Final fallback to basic pytesseract
        if PYTESSERACT_AVAILABLE and PIL_AVAILABLE:
            try:
                img_bytes = self._page_to_image_bytes(page)
                if img_bytes:
                    image = Image.open(io.BytesIO(img_bytes))
                    text = pytesseract.image_to_string(image, lang=self.lang_tesseract)
                    if text.strip():
                        logger.debug(f"Basic pytesseract extracted {len(text)} characters")
                        return text
            except Exception as e:
                logger.warning(f"Basic pytesseract extraction failed: {e}")
        
        logger.warning("No OCR engine available, returning empty text")
        return ""
    
    @staticmethod
    def is_ocr_available() -> bool:
        """Check if any OCR engine is available"""
        return PADDLEOCR_AVAILABLE or PYTESSERACT_AVAILABLE
    
    def _sort_lines_by_position(self, ocr_result: List, text_lines: List[str]) -> List[str]:
        """
        Sort OCR lines by their vertical position (top to bottom).
        
        Args:
            ocr_result: Raw OCR result
            text_lines: List of text lines
            
        Returns:
            Sorted list of text lines
        """
        try:
            # Create list of (y_position, text) tuples
            line_positions = []
            for i, line in enumerate(ocr_result):
                if len(line) >= 2 and i < len(text_lines):
                    bbox = line[0]
                    # Get top Y coordinate
                    y_pos = min(point[1] for point in bbox)
                    line_positions.append((y_pos, text_lines[i]))
            
            # Sort by Y position
            line_positions.sort(key=lambda x: x[0])
            
            return [text for _, text in line_positions]
            
        except Exception as e:
            logger.warning(f"Error sorting OCR lines: {e}")
            return text_lines
    
    def get_page_count(self) -> int:
        """
        Get the number of pages in the PDF.
        
        Returns:
            Number of pages
        """
        if not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF not available. Cannot get page count.")
            return 0
            
        try:
            doc = fitz.open(str(self.path))
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            logger.warning(f"Error getting page count: {e}")
            return 0
    
    def extract_page(self, page_num: int) -> str:
        """
        Extract text from a specific page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            Text content from the specified page
        """
        if not PYMUPDF_AVAILABLE:
            raise ExtractionError("PyMuPDF not available. Cannot process PDF files.", str(self.path))
            
        try:
            doc = fitz.open(str(self.path))
            
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} does not exist")
            
            page = doc[page_num]
            text = page.get_text()
            
            # Ensure text is a string
            if isinstance(text, (list, dict)):
                text = str(text)
            
            if not self._page_has_textlayer(page):
                text = self._extract_with_ocr(page)
            
            doc.close()
            return text
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract page {page_num}: {e}", str(self.path), e)
    
    @staticmethod
    def get_installation_instructions() -> str:
        """
        Get installation instructions for OCR dependencies.
        
        Returns:
            Installation command string
        """
        if PADDLEOCR_AVAILABLE:
            return "PaddleOCR is already installed"
        elif PYTESSERACT_AVAILABLE:
            return "pytesseract is available. For better OCR, install PaddleOCR: pip install paddleocr paddlepaddle"
        else:
            return "Install OCR: pip install paddleocr paddlepaddle OR pip install pytesseract"
