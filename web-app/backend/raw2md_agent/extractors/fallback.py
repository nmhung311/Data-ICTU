"""
Fallback text extractor for Raw2MD Agent.

Safe text reading with multi-encoding detection for unknown file types.
"""

import logging
from typing import Optional, Dict, Any

from .base import BaseExtractor, ExtractionError

logger = logging.getLogger(__name__)

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
    logger.warning("chardet not available. Fallback extraction will be limited.")


class FallbackExtractor(BaseExtractor):
    """
    Fallback text extractor for unknown file types.
    
    Features:
    - Safe text reading with multi-encoding detection
    - Fallback encoding strategies
    - Binary file detection
    - Text normalization
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Fallback extractor.
        
        Args:
            path: Path to file
            config: Optional configuration dictionary
        """
        super().__init__(path, config)
        
        # Fallback configuration
        self.max_file_size = config.get('max_file_size', 10 * 1024 * 1024) if config else 10 * 1024 * 1024  # 10MB
        self.fallback_encodings = config.get('fallback_encodings', [
            'utf-8', 'utf-16', 'cp1252', 'iso-8859-1', 'ascii', 'latin1'
        ]) if config else ['utf-8', 'utf-16', 'cp1252', 'iso-8859-1', 'ascii', 'latin1']
    
    def extract(self) -> str:
        """
        Extract text using fallback methods.
        
        Returns:
            Extracted text content
            
        Raises:
            ExtractionError: If extraction fails
        """
        try:
            # Check file size
            file_size = self.get_file_size()
            if file_size > self.max_file_size:
                raise ExtractionError(f"File too large: {file_size} bytes (max: {self.max_file_size})", str(self.path))
            
            # Check if file is likely binary
            if self._is_binary_file():
                raise ExtractionError("File appears to be binary, cannot extract text", str(self.path))
            
            # Try to read as text
            text_content = self._read_as_text()
            
            if not text_content.strip():
                raise ExtractionError("No readable text content found", str(self.path))
            
            # Normalize text
            normalized_text = self._normalize_text(text_content)
            
            logger.info(f"Successfully extracted {len(normalized_text)} characters using fallback method")
            return normalized_text
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract text using fallback method: {e}", str(self.path), e)
    
    def _is_binary_file(self) -> bool:
        """
        Check if file is likely binary.
        
        Returns:
            True if file appears to be binary
        """
        try:
            with open(self.path, 'rb') as f:
                # Read first 1024 bytes
                sample = f.read(1024)
            
            if not sample:
                return True
            
            # Check for null bytes (strong indicator of binary)
            if b'\x00' in sample:
                return True
            
            # Check for high ratio of non-printable characters
            printable_chars = sum(1 for byte in sample if 32 <= byte <= 126 or byte in [9, 10, 13])
            total_chars = len(sample)
            
            if total_chars > 0:
                printable_ratio = printable_chars / total_chars
                if printable_ratio < 0.7:  # Less than 70% printable
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking if file is binary: {e}")
            return False
    
    def _read_as_text(self) -> str:
        """
        Read file as text using multiple encoding strategies.
        
        Returns:
            File content as string
        """
        # Strategy 1: Try to detect encoding
        if CHARDET_AVAILABLE:
            try:
                with open(self.path, 'rb') as f:
                    sample = f.read(10000)  # Read first 10KB
                
                if sample:
                    result = chardet.detect(sample)
                    detected_encoding = result.get('encoding')
                    confidence = result.get('confidence', 0)
                    
                    if detected_encoding and confidence > 0.7:
                        logger.debug(f"Detected encoding: {detected_encoding} (confidence: {confidence:.2f})")
                        try:
                            with open(self.path, 'r', encoding=detected_encoding, errors='strict') as f:
                                return f.read()
                        except UnicodeDecodeError:
                            logger.warning(f"Failed to read with detected encoding {detected_encoding}")
            except Exception as e:
                logger.warning(f"Error in encoding detection: {e}")
        
        # Strategy 2: Try fallback encodings
        for encoding in self.fallback_encodings:
            try:
                with open(self.path, 'r', encoding=encoding, errors='strict') as f:
                    content = f.read()
                    logger.debug(f"Successfully read file with encoding: {encoding}")
                    return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Error reading with encoding {encoding}: {e}")
        
        # Strategy 3: Read with error replacement
        try:
            with open(self.path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                logger.warning("Read file with error replacement using UTF-8")
                return content
        except Exception as e:
            raise ExtractionError(f"Failed to read file with any encoding: {e}", str(self.path), e)
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize extracted text.
        
        Args:
            text: Raw text content
            
        Returns:
            Normalized text content
        """
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            # Strip trailing whitespace
            line = line.rstrip()
            
            # Skip empty lines (but preserve paragraph structure)
            if not line:
                if normalized_lines and normalized_lines[-1] != '':
                    normalized_lines.append('')
                continue
            
            # Normalize internal whitespace
            line = ' '.join(line.split())
            normalized_lines.append(line)
        
        # Remove trailing empty lines
        while normalized_lines and not normalized_lines[-1]:
            normalized_lines.pop()
        
        return '\n'.join(normalized_lines)
    
    def get_file_type_hint(self) -> str:
        """
        Get a hint about the file type based on content analysis.
        
        Returns:
            File type hint string
        """
        try:
            with open(self.path, 'rb') as f:
                header = f.read(100)
            
            # Check for common file signatures
            if header.startswith(b'%PDF-'):
                return 'pdf'
            elif header.startswith(b'PK\x03\x04'):
                return 'zip_or_docx'
            elif header.startswith(b'<html') or header.startswith(b'<!DOCTYPE html'):
                return 'html'
            elif header.startswith(b'<?xml') or header.startswith(b'<'):
                return 'xml'
            elif header.startswith(b'{') or header.startswith(b'['):
                return 'json'
            elif header.startswith(b'\xff\xd8\xff'):  # JPEG
                return 'image'
            elif header.startswith(b'\x89PNG'):  # PNG
                return 'image'
            elif b',' in header and b'\n' in header:
                return 'csv'
            else:
                return 'text'
                
        except Exception as e:
            logger.warning(f"Error getting file type hint: {e}")
            return 'unknown'
    
    def is_readable_text(self) -> bool:
        """
        Check if file contains readable text.
        
        Returns:
            True if file appears to contain readable text
        """
        try:
            # Quick check: read first 1000 characters
            text_sample = self._read_as_text()[:1000]
            
            if not text_sample.strip():
                return False
            
            # Check if sample contains mostly printable characters
            printable_chars = sum(1 for char in text_sample if char.isprintable() or char.isspace())
            total_chars = len(text_sample)
            
            if total_chars > 0:
                printable_ratio = printable_chars / total_chars
                return printable_ratio > 0.8  # More than 80% printable
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking if text is readable: {e}")
            return False
