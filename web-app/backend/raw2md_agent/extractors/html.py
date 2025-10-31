"""
HTML to Markdown conversion for Raw2MD Agent.

Uses html2text to convert HTML content to clean Markdown format.
"""

import logging
from typing import Optional, Dict, Any

from .base import BaseExtractor, ExtractionError, CorruptedFileError

logger = logging.getLogger(__name__)

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False
    logger.warning("html2text not available. HTML extraction will not work.")


class HTMLExtractor(BaseExtractor):
    """
    HTML to Markdown converter using html2text.
    
    Features:
    - Convert HTML to clean Markdown
    - Preserve table structure
    - Handle links and images
    - Clean up formatting
    """
    
    def __init__(self, path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize HTML extractor.
        
        Args:
            path: Path to HTML file
            config: Optional configuration dictionary
        """
        super().__init__(path, config)
        
        if not HTML2TEXT_AVAILABLE:
            raise ExtractionError("html2text library not available", str(self.path))
        
        # Configure html2text
        self.h = html2text.HTML2Text()
        self.h.ignore_links = config.get('ignore_links', False) if config else False
        self.h.ignore_images = config.get('ignore_images', False) if config else False
        self.h.ignore_tables = config.get('ignore_tables', False) if config else False
        self.h.body_width = config.get('body_width', 0) if config else 0
        self.h.unicode_snob = True
        self.h.escape_snob = True
    
    def extract(self) -> str:
        """
        Extract and convert HTML to Markdown.
        
        Returns:
            Converted Markdown content
            
        Raises:
            ExtractionError: If extraction fails
            CorruptedFileError: If HTML is corrupted
        """
        try:
            # Read HTML content
            with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            if not html_content.strip():
                raise ExtractionError("HTML file is empty", str(self.path))
            
            # Convert to Markdown
            markdown_content = self.h.handle(html_content)
            
            # Clean up the output
            markdown_content = self._clean_markdown(markdown_content)
            
            if not markdown_content.strip():
                raise ExtractionError("No content found after HTML conversion", str(self.path))
            
            logger.info(f"Successfully converted HTML to {len(markdown_content)} characters of Markdown")
            return markdown_content
            
        except UnicodeDecodeError as e:
            raise CorruptedFileError(f"HTML file encoding error: {e}", str(self.path), e)
        except Exception as e:
            raise ExtractionError(f"Failed to extract text from HTML: {e}", str(self.path), e)
    
    def _clean_markdown(self, markdown: str) -> str:
        """
        Clean up converted Markdown content.
        
        Args:
            markdown: Raw Markdown content
            
        Returns:
            Cleaned Markdown content
        """
        lines = markdown.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove excessive whitespace
            line = line.strip()
            
            # Skip empty lines (but preserve some structure)
            if not line:
                if cleaned_lines and cleaned_lines[-1] != '':
                    cleaned_lines.append('')
                continue
            
            # Clean up common HTML artifacts
            line = line.replace('&nbsp;', ' ')
            line = line.replace('&amp;', '&')
            line = line.replace('&lt;', '<')
            line = line.replace('&gt;', '>')
            line = line.replace('&quot;', '"')
            
            # Remove excessive asterisks (common html2text artifact)
            while '****' in line:
                line = line.replace('****', '**')
            
            cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def extract_from_string(self, html_content: str) -> str:
        """
        Extract Markdown from HTML string content.
        
        Args:
            html_content: HTML content as string
            
        Returns:
            Converted Markdown content
        """
        try:
            markdown_content = self.h.handle(html_content)
            return self._clean_markdown(markdown_content)
        except Exception as e:
            raise ExtractionError(f"Failed to convert HTML string: {e}", str(self.path), e)
    
    def get_title(self) -> Optional[str]:
        """
        Extract title from HTML document.
        
        Returns:
            Document title or None
        """
        try:
            with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Simple title extraction
            import re
            title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up HTML entities
                title = title.replace('&nbsp;', ' ')
                title = title.replace('&amp;', '&')
                title = title.replace('&lt;', '<')
                title = title.replace('&gt;', '>')
                title = title.replace('&quot;', '"')
                return title
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting title: {e}")
            return None
