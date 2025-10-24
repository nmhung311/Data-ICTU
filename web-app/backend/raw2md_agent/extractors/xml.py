"""
XML text extraction for Raw2MD Agent.

Uses BeautifulSoup/lxml to extract text content from XML files while preserving structure.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .base import BaseExtractor, ExtractionError, CorruptedFileError

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    logger.warning("BeautifulSoup not available. XML extraction will not work.")


class XMLExtractor(BaseExtractor):
    """
    XML text extractor using BeautifulSoup.
    
    Features:
    - Extract text from XML nodes
    - Preserve document structure
    - Handle namespaces
    - Clean up formatting
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize XML extractor.
        
        Args:
            path: Path to XML file
            config: Optional configuration dictionary
        """
        super().__init__(path, config)
        
        if not BEAUTIFULSOUP_AVAILABLE:
            raise ExtractionError("BeautifulSoup library not available", str(self.path))
        
        # XML configuration
        self.preserve_structure = config.get('preserve_structure', True) if config else True
        self.include_attributes = config.get('include_attributes', False) if config else False
        self.encoding = config.get('encoding', 'utf-8') if config else 'utf-8'
    
    def extract(self) -> str:
        """
        Extract text from XML file.
        
        Returns:
            Extracted text content
            
        Raises:
            ExtractionError: If extraction fails
            CorruptedFileError: If XML is corrupted
        """
        try:
            # Read XML content
            with open(self.path, 'r', encoding=self.encoding, errors='ignore') as f:
                xml_content = f.read()
            
            if not xml_content.strip():
                raise ExtractionError("XML file is empty", str(self.path))
            
            # Parse XML
            if not BEAUTIFULSOUP_AVAILABLE:
                raise ExtractionError("BeautifulSoup library not available", str(self.path))
                
            soup = BeautifulSoup(xml_content, 'xml')
            
            # Extract text based on configuration
            if self.preserve_structure:
                extracted_text = self._extract_with_structure(soup)
            else:
                extracted_text = soup.get_text()
            
            # Clean up the text
            cleaned_text = self._clean_text(extracted_text)
            
            if not cleaned_text.strip():
                raise ExtractionError("No text content found in XML", str(self.path))
            
            logger.info(f"Successfully extracted {len(cleaned_text)} characters from XML")
            return cleaned_text
            
        except Exception as e:
            if "not well-formed" in str(e).lower() or "invalid" in str(e).lower():
                raise CorruptedFileError(f"XML file appears to be corrupted: {e}", str(self.path), e)
            raise ExtractionError(f"Failed to extract text from XML: {e}", str(self.path), e)
    
    def _extract_with_structure(self, soup) -> str:
        """
        Extract text while preserving XML structure.
        
        Args:
            soup: BeautifulSoup parsed XML
            
        Returns:
            Structured text content
        """
        lines = []
        
        # Extract root element info
        root = soup.find()
        if root:
            lines.append(f"# {root.name}")
            if self.include_attributes and root.attrs:
                attrs = ', '.join(f"{k}={v}" for k, v in root.attrs.items())
                lines.append(f"**Attributes:** {attrs}")
            lines.append("")
        
        # Extract all text nodes with structure
        for element in soup.find_all():
            if element.string and element.string.strip():
                # Determine heading level based on nesting
                level = len(element.find_parents()) + 1
                heading_prefix = '#' * min(level, 6)
                
                # Add element name as heading
                lines.append(f"{heading_prefix} {element.name}")
                
                # Add attributes if requested
                if self.include_attributes and element.attrs:
                    attrs = ', '.join(f"{k}={v}" for k, v in element.attrs.items())
                    lines.append(f"**Attributes:** {attrs}")
                
                # Add text content
                text = element.get_text().strip()
                if text:
                    lines.append(text)
                lines.append("")
        
        return '\n'.join(lines)
    
    def _clean_text(self, text: str) -> str:
        """
        Clean up extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text content
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Strip whitespace
            line = line.strip()
            
            # Skip empty lines (but preserve some structure)
            if not line:
                if cleaned_lines and cleaned_lines[-1] != '':
                    cleaned_lines.append('')
                continue
            
            # Clean up XML artifacts
            line = line.replace('&nbsp;', ' ')
            line = line.replace('&amp;', '&')
            line = line.replace('&lt;', '<')
            line = line.replace('&gt;', '>')
            line = line.replace('&quot;', '"')
            line = line.replace('&apos;', "'")
            
            cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def get_root_element(self) -> Optional[str]:
        """
        Get the root element name.
        
        Returns:
            Root element name or None
        """
        try:
            if not BEAUTIFULSOUP_AVAILABLE:
                return 0
                
            with open(self.path, 'r', encoding=self.encoding, errors='ignore') as f:
                xml_content = f.read()
            
            soup = BeautifulSoup(xml_content, 'xml')
            root = soup.find()
            
            return root.name if root else None
            
        except Exception as e:
            logger.warning(f"Error getting root element: {e}")
            return None
    
    def get_element_count(self) -> int:
        """
        Get the number of XML elements.
        
        Returns:
            Number of elements
        """
        try:
            if not BEAUTIFULSOUP_AVAILABLE:
                return 0
                
            with open(self.path, 'r', encoding=self.encoding, errors='ignore') as f:
                xml_content = f.read()
            
            soup = BeautifulSoup(xml_content, 'xml')
            return len(soup.find_all())
            
        except Exception as e:
            logger.warning(f"Error getting element count: {e}")
            return 0
    
    def extract_specific_elements(self, tag_names: list) -> str:
        """
        Extract text from specific XML elements.
        
        Args:
            tag_names: List of tag names to extract
            
        Returns:
            Extracted text from specified elements
        """
        try:
            if not BEAUTIFULSOUP_AVAILABLE:
                return 0
                
            with open(self.path, 'r', encoding=self.encoding, errors='ignore') as f:
                xml_content = f.read()
            
            soup = BeautifulSoup(xml_content, 'xml')
            
            extracted_texts = []
            for tag_name in tag_names:
                elements = soup.find_all(tag_name)
                for element in elements:
                    text = element.get_text().strip()
                    if text:
                        extracted_texts.append(f"**{tag_name}:** {text}")
            
            return '\n'.join(extracted_texts)
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract specific elements: {e}", str(self.path), e)
