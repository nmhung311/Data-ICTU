"""
Extractor factory and registry for Raw2MD Agent.

Provides a unified interface to get the appropriate extractor
for any supported file type.
"""

from typing import Dict, Type, Optional
from .base import BaseExtractor
from .fallback import FallbackExtractor
import logging

# Import extractors with error handling
try:
    from .pdf import PDFExtractor
except ImportError as e:
    logger.warning(f"PDFExtractor not available: {e}")
    PDFExtractor = None

try:
    from .docx import DOCXExtractor
except ImportError as e:
    logger.warning(f"DOCXExtractor not available: {e}")
    DOCXExtractor = None

try:
    from .html import HTMLExtractor
except ImportError as e:
    logger.warning(f"HTMLExtractor not available: {e}")
    HTMLExtractor = None

try:
    from .txt import TXTExtractor
except ImportError as e:
    logger.warning(f"TXTExtractor not available: {e}")
    TXTExtractor = None

try:
    from .csv import CSVExtractor
except ImportError as e:
    logger.warning(f"CSVExtractor not available: {e}")
    CSVExtractor = None

try:
    from .xml import XMLExtractor
except ImportError as e:
    logger.warning(f"XMLExtractor not available: {e}")
    XMLExtractor = None

try:
    from .json import JSONExtractor
except ImportError as e:
    logger.warning(f"JSONExtractor not available: {e}")
    JSONExtractor = None

try:
    from .image import ImageExtractor
except ImportError as e:
    logger.warning(f"ImageExtractor not available: {e}")
    ImageExtractor = None

logger = logging.getLogger(__name__)

# Registry of available extractors
EXTRACTOR_REGISTRY: Dict[str, Type[BaseExtractor]] = {
    'unknown': FallbackExtractor,
}

# Add available extractors to registry
if PDFExtractor is not None:
    EXTRACTOR_REGISTRY['pdf'] = PDFExtractor
if DOCXExtractor is not None:
    EXTRACTOR_REGISTRY['docx'] = DOCXExtractor
if HTMLExtractor is not None:
    EXTRACTOR_REGISTRY['html'] = HTMLExtractor
if TXTExtractor is not None:
    EXTRACTOR_REGISTRY['txt'] = TXTExtractor
if CSVExtractor is not None:
    EXTRACTOR_REGISTRY['csv'] = CSVExtractor
if XMLExtractor is not None:
    EXTRACTOR_REGISTRY['xml'] = XMLExtractor
if JSONExtractor is not None:
    EXTRACTOR_REGISTRY['json'] = JSONExtractor
if ImageExtractor is not None:
    EXTRACTOR_REGISTRY['image'] = ImageExtractor


def get_extractor(file_type: str, file_path: str, config: Optional[Dict] = None) -> BaseExtractor:
    """
    Get the appropriate extractor for a file type.
    
    Args:
        file_type: Type of file (pdf, docx, html, etc.)
        file_path: Path to the file
        config: Optional configuration dictionary
        
    Returns:
        Extractor instance for the file type
        
    Raises:
        ValueError: If file type is not supported
    """
    if file_type not in EXTRACTOR_REGISTRY:
        logger.warning(f"Unsupported file type: {file_type}, using fallback extractor")
        file_type = 'unknown'
    
    extractor_class = EXTRACTOR_REGISTRY[file_type]
    logger.debug(f"Using {extractor_class.__name__} for file type: {file_type}")
    
    return extractor_class(file_path, config)


def register_extractor(file_type: str, extractor_class: Type[BaseExtractor]) -> None:
    """
    Register a new extractor for a file type.
    
    Args:
        file_type: File type string
        extractor_class: Extractor class that inherits from BaseExtractor
    """
    if not issubclass(extractor_class, BaseExtractor):
        raise ValueError("Extractor class must inherit from BaseExtractor")
    
    EXTRACTOR_REGISTRY[file_type] = extractor_class
    logger.info(f"Registered extractor {extractor_class.__name__} for file type: {file_type}")


def get_supported_types() -> list:
    """
    Get list of supported file types.
    
    Returns:
        List of supported file type strings
    """
    return list(EXTRACTOR_REGISTRY.keys())


def is_supported(file_type: str) -> bool:
    """
    Check if a file type is supported.
    
    Args:
        file_type: File type string
        
    Returns:
        True if supported, False otherwise
    """
    return file_type in EXTRACTOR_REGISTRY


# Export main functions
__all__ = [
    'BaseExtractor',
    'get_extractor',
    'register_extractor',
    'get_supported_types',
    'is_supported',
    'EXTRACTOR_REGISTRY',
]