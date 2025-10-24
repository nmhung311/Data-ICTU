"""
Base extractor class and exceptions for Raw2MD Agent.

Provides the foundation for all file type extractors.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """
    Exception raised when text extraction fails.
    
    Attributes:
        message: Error message
        file_path: Path to the file that caused the error
        original_error: Original exception that caused this error (optional)
    """
    
    def __init__(self, message: str, file_path: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        self.original_error = original_error


class CorruptedFileError(ExtractionError):
    """
    Exception raised when a file appears to be corrupted or invalid.
    
    This is a specialized ExtractionError for files that cannot be processed
    due to corruption or format issues.
    """
    
    def __init__(self, message: str, file_path: str, original_error: Optional[Exception] = None):
        super().__init__(message, file_path, original_error)


class BaseExtractor(ABC):
    """
    Abstract base class for all file extractors.
    
    Provides common functionality and interface for extracting text
    from various file formats.
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the extractor.
        
        Args:
            path: Path to the file to extract text from
            config: Optional configuration dictionary
        """
        self.path = Path(path)
        self.config = config or {}
        
        # Validate file exists
        if not self.path.exists():
            raise ExtractionError(f"File does not exist: {path}", str(self.path))
        
        if not self.path.is_file():
            raise ExtractionError(f"Path is not a file: {path}", str(self.path))
    
    @abstractmethod
    def extract(self) -> str:
        """
        Extract text from the file.
        
        Returns:
            Extracted text content
            
        Raises:
            ExtractionError: If extraction fails
            CorruptedFileError: If file is corrupted
        """
        pass
    
    def get_file_size(self) -> int:
        """
        Get the size of the file in bytes.
        
        Returns:
            File size in bytes
        """
        try:
            return self.path.stat().st_size
        except Exception as e:
            logger.warning(f"Error getting file size: {e}")
            return 0
    
    def get_file_extension(self) -> str:
        """
        Get the file extension (without the dot).
        
        Returns:
            File extension in lowercase
        """
        return self.path.suffix.lower().lstrip('.')
    
    def get_file_name(self) -> str:
        """
        Get the file name (without path).
        
        Returns:
            File name
        """
        return self.path.name
    
    def is_empty(self) -> bool:
        """
        Check if the file is empty.
        
        Returns:
            True if file is empty
        """
        return self.get_file_size() == 0
    
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
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
        
        # Normalize text
        cleaned = self._normalize_text(text)
        
        # Remove excessive blank lines (more than 2 consecutive)
        lines = cleaned.split('\n')
        cleaned_lines = []
        blank_count = 0
        
        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:  # Allow up to 2 consecutive blank lines
                    cleaned_lines.append(line)
            else:
                blank_count = 0
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get basic metadata about the file.
        
        Returns:
            Dictionary containing file metadata
        """
        try:
            stat = self.path.stat()
            return {
                'file_name': self.get_file_name(),
                'file_extension': self.get_file_extension(),
                'file_size': self.get_file_size(),
                'is_empty': self.is_empty(),
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
            }
        except Exception as e:
            logger.warning(f"Error getting file metadata: {e}")
            return {
                'file_name': self.get_file_name(),
                'file_extension': self.get_file_extension(),
                'file_size': 0,
                'is_empty': True,
                'error': str(e)
            }
    
    def __str__(self) -> str:
        """String representation of the extractor."""
        return f"{self.__class__.__name__}({self.path})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the extractor."""
        return f"{self.__class__.__name__}(path='{self.path}', config={self.config})"
