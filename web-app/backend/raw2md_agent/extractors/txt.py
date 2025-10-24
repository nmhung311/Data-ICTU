"""
Plain text extraction with encoding detection for Raw2MD Agent.

Uses chardet for encoding detection and handles various text formats.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .base import BaseExtractor, ExtractionError, CorruptedFileError

logger = logging.getLogger(__name__)

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
    logger.warning("chardet not available. Encoding detection will be limited.")


class TXTExtractor(BaseExtractor):
    """
    Plain text extractor with automatic encoding detection.
    
    Features:
    - Automatic encoding detection using chardet
    - Support for UTF-8, UTF-16, CP1252, and other encodings
    - Fallback encoding strategies
    - Text normalization
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize TXT extractor.
        
        Args:
            path: Path to text file
            config: Optional configuration dictionary
        """
        super().__init__(path, config)
        
        # Encoding configuration
        self.default_encoding = config.get('default_encoding', 'utf-8') if config else 'utf-8'
        self.fallback_encodings = config.get('fallback_encodings', [
            'utf-8', 'utf-16', 'cp1252', 'iso-8859-1', 'ascii'
        ]) if config else ['utf-8', 'utf-16', 'cp1252', 'iso-8859-1', 'ascii']
        
        self.detected_encoding = None
    
    def extract(self) -> str:
        """
        Extract text from file with encoding detection.
        
        Returns:
            Extracted text content
            
        Raises:
            ExtractionError: If extraction fails
            CorruptedFileError: If file is corrupted
        """
        try:
            # Detect encoding
            encoding = self._detect_encoding()
            self.detected_encoding = encoding
            
            # Read file with detected encoding
            text_content = self._read_with_encoding(encoding)
            
            if not text_content.strip():
                raise ExtractionError("Text file is empty", str(self.path))
            
            # Normalize text
            normalized_text = self._normalize_text(text_content)
            
            logger.info(f"Successfully extracted {len(normalized_text)} characters from text file (encoding: {encoding})")
            return normalized_text
            
        except UnicodeDecodeError as e:
            raise CorruptedFileError(f"Text file encoding error: {e}", str(self.path), e)
        except Exception as e:
            raise ExtractionError(f"Failed to extract text from file: {e}", str(self.path), e)
    
    def _detect_encoding(self) -> str:
        """
        Detect file encoding using chardet.
        
        Returns:
            Detected encoding string
        """
        if not CHARDET_AVAILABLE:
            logger.warning("chardet not available, using default encoding")
            return self.default_encoding
        
        try:
            # Read a sample of the file for detection
            with open(self.path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB
            
            if not raw_data:
                return self.default_encoding
            
            # Detect encoding
            result = chardet.detect(raw_data)
            detected_encoding = result.get('encoding', self.default_encoding)
            confidence = result.get('confidence', 0)
            
            logger.debug(f"Detected encoding: {detected_encoding} (confidence: {confidence:.2f})")
            
            # Use detected encoding if confidence is high enough
            if confidence > 0.7:
                return detected_encoding
            else:
                logger.warning(f"Low confidence encoding detection ({confidence:.2f}), using default")
                return self.default_encoding
                
        except Exception as e:
            logger.warning(f"Error detecting encoding: {e}")
            return self.default_encoding
    
    def _read_with_encoding(self, encoding: str) -> str:
        """
        Read file with specified encoding, with fallback strategies.
        
        Args:
            encoding: Encoding to use
            
        Returns:
            File content as string
        """
        # Try the detected/default encoding first
        try:
            with open(self.path, 'r', encoding=encoding, errors='strict') as f:
                return f.read()
        except UnicodeDecodeError:
            logger.warning(f"Failed to read with {encoding}, trying fallback encodings")
        
        # Try fallback encodings
        for fallback_encoding in self.fallback_encodings:
            if fallback_encoding == encoding:
                continue
                
            try:
                with open(self.path, 'r', encoding=fallback_encoding, errors='strict') as f:
                    content = f.read()
                    logger.info(f"Successfully read file with fallback encoding: {fallback_encoding}")
                    return content
            except UnicodeDecodeError:
                continue
        
        # Last resort: read with error replacement
        try:
            with open(self.path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
                logger.warning(f"Read file with error replacement using {encoding}")
                return content
        except Exception as e:
            raise ExtractionError(f"Failed to read file with any encoding: {e}", str(self.path), e)
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text content.
        
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
    
    def get_encoding(self) -> Optional[str]:
        """
        Get the detected encoding.
        
        Returns:
            Detected encoding or None if not yet detected
        """
        return self.detected_encoding
    
    def get_line_count(self) -> int:
        """
        Get the number of lines in the file.
        
        Returns:
            Number of lines
        """
        try:
            encoding = self._detect_encoding()
            with open(self.path, 'r', encoding=encoding, errors='replace') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.warning(f"Error getting line count: {e}")
            return 0
