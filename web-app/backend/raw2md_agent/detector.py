"""
File type detection module for Raw2MD Agent.

Detects file types using MIME types, file extensions, and content analysis.
Supports: pdf, docx, html, txt, csv, xml, json, image, unknown
"""

import mimetypes
from pathlib import Path
from typing import Dict, Set, Union
import logging

logger = logging.getLogger(__name__)

# File type mappings
FILE_TYPE_MAPPINGS: Dict[str, Set[str]] = {
    'pdf': {'.pdf'},
    'docx': {'.docx', '.doc'},
    'html': {'.html', '.htm'},
    'txt': {'.txt', '.md', '.rtf'},
    'csv': {'.csv', '.tsv'},
    'xml': {'.xml', '.xhtml'},
    'json': {'.json'},
    'image': {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp', '.gif'},
}

# MIME type mappings
MIME_TYPE_MAPPINGS: Dict[str, Set[str]] = {
    'pdf': {'application/pdf'},
    'docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
             'application/msword'},
    'html': {'text/html', 'application/xhtml+xml'},
    'txt': {'text/plain', 'text/markdown', 'application/rtf'},
    'csv': {'text/csv', 'application/csv'},
    'xml': {'application/xml', 'text/xml', 'application/xhtml+xml'},
    'json': {'application/json'},
    'image': {'image/jpeg', 'image/png', 'image/tiff', 'image/bmp', 
              'image/webp', 'image/gif'},
}


def detect_type(file_path: str) -> str:
    """
    Detect file type using multiple methods.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        File type string: pdf, docx, html, txt, csv, xml, json, image, unknown
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    # Method 1: File extension
    extension_type = _detect_by_extension(path)
    if extension_type != 'unknown':
        logger.debug(f"Detected type by extension: {extension_type}")
        return extension_type
    
    # Method 2: MIME type
    mime_type = _detect_by_mime_type(path)
    if mime_type != 'unknown':
        logger.debug(f"Detected type by MIME: {mime_type}")
        return mime_type
    
    # Method 3: Content analysis (magic bytes)
    content_type = _detect_by_content(path)
    if content_type != 'unknown':
        logger.debug(f"Detected type by content: {content_type}")
        return content_type
    
    logger.warning(f"Could not detect file type for: {file_path}")
    return 'unknown'


def _detect_by_extension(path: Path) -> str:
    """Detect file type by extension."""
    suffix = path.suffix.lower()
    
    for file_type, extensions in FILE_TYPE_MAPPINGS.items():
        if suffix in extensions:
            return file_type
    
    return 'unknown'


def _detect_by_mime_type(path: Path) -> str:
    """Detect file type by MIME type."""
    try:
        # Use Python's mimetypes module
        mime_type, _ = mimetypes.guess_type(str(path))
        
        if mime_type:
            for file_type, mime_types in MIME_TYPE_MAPPINGS.items():
                if mime_type in mime_types:
                    return file_type
        
        # Try python-magic if available
        try:
            import magic
            mime_type = magic.from_file(str(path), mime=True)
            
            for file_type, mime_types in MIME_TYPE_MAPPINGS.items():
                if mime_type in mime_types:
                    return file_type
        except ImportError:
            logger.debug("python-magic not available, skipping content-based detection")
        except Exception as e:
            logger.warning(f"Error using python-magic: {e}")
            
    except Exception as e:
        logger.warning(f"Error detecting MIME type: {e}")
    
    return 'unknown'


def _detect_by_content(path: Path) -> str:
    """Detect file type by analyzing file content."""
    try:
        with open(path, 'rb') as f:
            # Read first 1024 bytes for analysis
            header = f.read(1024)
            
            # PDF signature
            if header.startswith(b'%PDF-'):
                return 'pdf'
            
            # DOCX signature (ZIP-based)
            if header.startswith(b'PK\x03\x04') and b'word/' in header:
                return 'docx'
            
            # HTML signature
            if header.startswith(b'<html') or header.startswith(b'<!DOCTYPE html'):
                return 'html'
            
            # XML signature
            if header.startswith(b'<?xml') or header.startswith(b'<'):
                # Check if it's HTML or XML
                content_str = header.decode('utf-8', errors='ignore').lower()
                if 'html' in content_str or 'doctype' in content_str:
                    return 'html'
                return 'xml'
            
            # JSON signature
            if header.startswith(b'{') or header.startswith(b'['):
                return 'json'
            
            # Image signatures
            if header.startswith(b'\xff\xd8\xff'):  # JPEG
                return 'image'
            if header.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                return 'image'
            if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):  # GIF
                return 'image'
            if header.startswith(b'BM'):  # BMP
                return 'image'
            if header.startswith(b'RIFF') and b'WEBP' in header:  # WebP
                return 'image'
            
            # TIFF signatures
            if header.startswith(b'II*\x00') or header.startswith(b'MM\x00*'):
                return 'image'
            
            # CSV detection (simple heuristic)
            try:
                content_str = header.decode('utf-8', errors='ignore')
                lines = content_str.split('\n')[:5]  # Check first 5 lines
                if len(lines) >= 2:
                    # Check if lines have consistent comma/tab separation
                    separators = [',', '\t', ';']
                    for sep in separators:
                        if all(sep in line for line in lines if line.strip()):
                            return 'csv'
            except:
                pass
            
            # Default to text if it's readable
            try:
                content_str = header.decode('utf-8', errors='ignore')
                if content_str.isprintable() or '\n' in content_str:
                    return 'txt'
            except:
                pass
                
    except Exception as e:
        logger.warning(f"Error analyzing file content: {e}")
    
    return 'unknown'


def is_supported_format(file_type: str) -> bool:
    """
    Check if a file type is supported for processing.
    
    Args:
        file_type: File type string
        
    Returns:
        True if supported, False otherwise
    """
    supported_types = {'pdf', 'docx', 'html', 'txt', 'csv', 'xml', 'json', 'image'}
    return file_type in supported_types


def get_file_info(file_path: str) -> Dict[str, Union[str, int, bool]]:
    """
    Get comprehensive file information.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    path = Path(file_path)
    
    return {
        'path': str(path.absolute()),
        'name': path.name,
        'stem': path.stem,
        'suffix': path.suffix,
        'size_bytes': path.stat().st_size if path.exists() else 0,
        'type': detect_type(file_path),
        'supported': is_supported_format(detect_type(file_path)),
    }
