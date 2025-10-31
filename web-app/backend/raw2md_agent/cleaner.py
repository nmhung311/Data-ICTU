"""
Text cleaning pipeline for Raw2MD Agent.

Cleans and normalizes extracted text with Vietnamese legal structure preservation.
"""

import re
import logging
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Text cleaning pipeline for Vietnamese administrative documents.
    
    Features:
    - Header/footer removal
    - Page number removal
    - Duplicate line detection
    - Soft line break merging
    - Vietnamese legal structure preservation
    - Bullet list formatting
    - Whitespace normalization
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize text cleaner.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Vietnamese legal structure patterns
        self.legal_patterns = {
            'dieu': r'^Điều\s+(\d+)[\.:]?\s*(.*)$',
            'khoan': r'^(\d+)\.\s*(.*)$',
            'chuong': r'^Chương\s+([IVX\d]+)[\.:]?\s*(.*)$',
            'muc': r'^Mục\s+(\d+)[\.:]?\s*(.*)$',
            'phu_luc': r'^Phụ\s+lục\s+([IVX\d]+)[\.:]?\s*(.*)$',
        }
        
        # Header/footer patterns
        self.header_patterns = [
            r'^BỘ\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]+$',
            r'^CỘNG\s+HÒA\s+XÃ\s+HỘI\s+CHỦ\s+NGHĨA\s+VIỆT\s+NAM$',
            r'^Độc\s+lập\s*-\s*Tự\s+do\s*-\s*Hạnh\s+phúc$',
        ]
        
        self.footer_patterns = [
            r'^Trang\s+\d+\s+/\s+\d+$',
            r'^\d+\s*$',  # Page numbers
            r'^-\s*\d+\s*-$',  # Page numbers with dashes
        ]
        
        # Common OCR errors
        self.ocr_corrections = {
            'ngàỵ': 'ngày',
            'tháng 1O': 'tháng 10',
            'tháng 2O': 'tháng 20',
            'năm 2O': 'năm 20',
            'Điều 1O': 'Điều 10',
            'Điều 2O': 'Điều 20',
            'Khoản 1O': 'Khoản 10',
            'Khoản 2O': 'Khoản 20',
        }
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text content
        """
        if not text or not text.strip():
            return ""
        
        logger.debug("Starting text cleaning pipeline")
        
        # Step 1: Basic normalization
        cleaned_text = self._normalize_encoding(text)
        
        # Step 2: Fix common OCR errors
        cleaned_text = self._fix_ocr_errors(cleaned_text)
        
        # Step 3: Remove headers and footers
        cleaned_text = self._remove_headers_footers(cleaned_text)
        
        # Step 4: Remove page numbers
        cleaned_text = self._remove_page_numbers(cleaned_text)
        
        # Step 5: Merge soft line breaks
        cleaned_text = self._merge_soft_breaks(cleaned_text)
        
        # Step 6: Remove duplicate lines
        cleaned_text = self._remove_duplicate_lines(cleaned_text)
        
        # Step 7: Preserve Vietnamese legal structure
        cleaned_text = self._preserve_legal_structure(cleaned_text)
        
        # Step 8: Format bullet lists
        cleaned_text = self._format_bullet_lists(cleaned_text)
        
        # Step 9: Normalize whitespace
        cleaned_text = self._normalize_whitespace(cleaned_text)
        
        # Step 10: Collapse multiple blank lines
        cleaned_text = self._collapse_blank_lines(cleaned_text)
        
        logger.debug("Text cleaning pipeline completed")
        return cleaned_text
    
    def _normalize_encoding(self, text: str) -> str:
        """Normalize text encoding and line endings."""
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove BOM if present
        if text.startswith('\ufeff'):
            text = text[1:]
        
        return text
    
    def _fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors in Vietnamese text."""
        for error, correction in self.ocr_corrections.items():
            text = text.replace(error, correction)
        
        # Fix common digit OCR errors
        text = re.sub(r'(\d+)O(\d*)', r'\g<1>0\g<2>', text)  # 1O -> 10
        text = re.sub(r'(\d+)I(\d*)', r'\g<1>1\g<2>', text)  # 1I -> 11
        
        return text
    
    def _remove_headers_footers(self, text: str) -> str:
        """Remove common headers and footers."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Check header patterns
            is_header = any(re.match(pattern, line, re.IGNORECASE) for pattern in self.header_patterns)
            
            # Check footer patterns
            is_footer = any(re.match(pattern, line) for pattern in self.footer_patterns)
            
            if not is_header and not is_footer:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _remove_page_numbers(self, text: str) -> str:
        """Remove page numbers and page references."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip lines that are just page numbers
            if re.match(r'^\d+$', line):
                continue
            
            # Skip lines with page references
            if re.search(r'Trang\s+\d+', line, re.IGNORECASE):
                continue
            
            # Skip lines with page numbers at the end
            if re.search(r'\d+\s*$', line) and len(line) < 10:
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _merge_soft_breaks(self, text: str) -> str:
        """Merge soft line breaks within sentences."""
        lines = text.split('\n')
        merged_lines = []
        current_line = ""
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if current_line:
                    merged_lines.append(current_line)
                    current_line = ""
                merged_lines.append("")
                continue
            
            # Check if line ends with sentence-ending punctuation
            if re.match(r'.*[.!?]$', line):
                if current_line:
                    merged_lines.append(current_line + " " + line)
                    current_line = ""
                else:
                    merged_lines.append(line)
            else:
                # Check if line starts with lowercase (likely continuation)
                if line and line[0].islower() and current_line:
                    current_line += " " + line
                else:
                    if current_line:
                        merged_lines.append(current_line)
                    current_line = line
        
        # Add remaining line
        if current_line:
            merged_lines.append(current_line)
        
        return '\n'.join(merged_lines)
    
    def _remove_duplicate_lines(self, text: str) -> str:
        """Remove consecutive duplicate lines."""
        lines = text.split('\n')
        cleaned_lines = []
        previous_line = None
        
        for line in lines:
            if line != previous_line:
                cleaned_lines.append(line)
            previous_line = line
        
        return '\n'.join(cleaned_lines)
    
    def _preserve_legal_structure(self, text: str) -> str:
        """Preserve Vietnamese legal document structure."""
        lines = text.split('\n')
        structured_lines = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                structured_lines.append("")
                continue
            
            # Check for legal structure patterns
            formatted_line = self._format_legal_structure(line)
            structured_lines.append(formatted_line)
        
        return '\n'.join(structured_lines)
    
    def _format_legal_structure(self, line: str) -> str:
        """Format a line according to Vietnamese legal structure."""
        # Điều (Article)
        match = re.match(self.legal_patterns['dieu'], line, re.IGNORECASE)
        if match:
            number = match.group(1)
            content = match.group(2)
            return f"### Điều {number}. {content}"
        
        # Khoản (Clause)
        match = re.match(self.legal_patterns['khoan'], line)
        if match:
            number = match.group(1)
            content = match.group(2)
            return f"**{number}.** {content}"
        
        # Chương (Chapter)
        match = re.match(self.legal_patterns['chuong'], line, re.IGNORECASE)
        if match:
            number = match.group(1)
            content = match.group(2)
            return f"## Chương {number}. {content}"
        
        # Mục (Section)
        match = re.match(self.legal_patterns['muc'], line, re.IGNORECASE)
        if match:
            number = match.group(1)
            content = match.group(2)
            return f"### Mục {number}. {content}"
        
        # Phụ lục (Appendix)
        match = re.match(self.legal_patterns['phu_luc'], line, re.IGNORECASE)
        if match:
            number = match.group(1)
            content = match.group(2)
            return f"## Phụ lục {number}. {content}"
        
        return line
    
    def _format_bullet_lists(self, text: str) -> str:
        """Format bullet lists and numbered lists."""
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                formatted_lines.append("")
                continue
            
            # Check for bullet points
            if re.match(r'^[-•·]\s+', line):
                content = re.sub(r'^[-•·]\s+', '', line)
                formatted_lines.append(f"- {content}")
            # Check for numbered lists
            elif re.match(r'^\d+[\.)]\s+', line):
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace within lines."""
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            # Normalize internal whitespace
            line = ' '.join(line.split())
            normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    def _collapse_blank_lines(self, text: str) -> str:
        """Collapse multiple consecutive blank lines to single blank lines."""
        # Replace multiple newlines with double newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove leading and trailing whitespace
        text = text.strip()
        
        return text
    
    def get_text_statistics(self, text: str) -> Dict[str, Union[int, Dict[str, int]]]:
        """
        Get statistics about the cleaned text.
        
        Args:
            text: Cleaned text content
            
        Returns:
            Dictionary with text statistics
        """
        lines = text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        return {
            'total_lines': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'total_characters': len(text),
            'total_words': len(text.split()),
            'legal_structures': self._count_legal_structures(text),
        }
    
    def _count_legal_structures(self, text: str) -> Dict[str, int]:
        """Count Vietnamese legal structures in text."""
        counts = {}
        
        for structure_type, pattern in self.legal_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            counts[structure_type] = len(matches)
        
        return counts


def clean_text(text: str, config: Optional[Dict] = None) -> str:
    """
    Convenience function to clean text using the TextCleaner.
    
    Args:
        text: Raw text to clean
        config: Optional configuration dictionary
        
    Returns:
        Cleaned text content
    """
    cleaner = TextCleaner(config)
    return cleaner.clean_text(text)
