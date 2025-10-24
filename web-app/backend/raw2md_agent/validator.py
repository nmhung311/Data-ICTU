"""
Validation module for Raw2MD Agent.

Validates markdown output and metadata completeness.
"""

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DocumentValidator:
    """
    Document validator for markdown output.
    
    Features:
    - Metadata completeness validation
    - Markdown structure validation
    - UTF-8 encoding validation
    - Content quality checks
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize document validator.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.min_content_length = self.config.get('min_content_length', 100)
        self.required_metadata_fields = self.config.get('required_metadata_fields', [
            'doc_id', 'category', 'source', 'date', 'modify', 'partial_mod', 'data_type', 'amend'
        ])
    
    def validate(self, markdown_content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate markdown document and metadata.
        
        Args:
            markdown_content: Markdown content to validate
            metadata: Optional metadata dictionary
            
        Returns:
            Validation results dictionary
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'metadata_valid': True,
            'content_valid': True,
            'encoding_valid': True,
            'stats': {}
        }
        
        # Validate metadata
        if metadata:
            metadata_validation = self._validate_metadata(metadata)
            validation_result.update(metadata_validation)
        
        # Validate markdown structure
        structure_validation = self._validate_markdown_structure(markdown_content)
        validation_result.update(structure_validation)
        
        # Validate content quality
        content_validation = self._validate_content_quality(markdown_content)
        validation_result.update(content_validation)
        
        # Validate encoding
        encoding_validation = self._validate_encoding(markdown_content)
        validation_result.update(encoding_validation)
        
        # Overall validation
        validation_result['valid'] = (
            validation_result['metadata_valid'] and
            validation_result['content_valid'] and
            validation_result['encoding_valid']
        )
        
        return validation_result
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata completeness and format."""
        result = {
            'metadata_valid': True,
            'metadata_errors': [],
            'metadata_warnings': [],
        }
        
        # Check required fields
        for field in self.required_metadata_fields:
            if field not in metadata:
                result['metadata_errors'].append(f"Missing required metadata field: {field}")
                result['metadata_valid'] = False
            elif not metadata[field] and field not in ['modify', 'amend']:  # These can be empty
                result['metadata_warnings'].append(f"Empty metadata field: {field}")
        
        # Validate specific field formats
        if 'doc_id' in metadata and metadata['doc_id']:
            if not self._validate_doc_id_format(metadata['doc_id']):
                result['metadata_warnings'].append(f"Invalid doc_id format: {metadata['doc_id']}")
        
        if 'date' in metadata and metadata['date']:
            if not self._validate_date_format(metadata['date']):
                result['metadata_warnings'].append(f"Invalid date format: {metadata['date']}")
        
        if 'category' in metadata and metadata['category']:
            if not self._validate_category(metadata['category']):
                result['metadata_warnings'].append(f"Invalid category: {metadata['category']}")
        
        if 'partial_mod' in metadata:
            if not isinstance(metadata['partial_mod'], bool):
                result['metadata_errors'].append("partial_mod must be boolean")
                result['metadata_valid'] = False
        
        if 'data_type' in metadata and metadata['data_type'] != 'markdown':
            result['metadata_warnings'].append(f"Unexpected data_type: {metadata['data_type']}")
        
        return result
    
    def _validate_markdown_structure(self, content: str) -> Dict[str, Any]:
        """Validate markdown structure."""
        result = {
            'content_valid': True,
            'structure_errors': [],
            'structure_warnings': [],
        }
        
        # Check for required sections
        has_metadata = '## Metadata' in content
        has_content = '## Nội dung' in content
        
        if not has_metadata:
            result['structure_errors'].append("Missing metadata section")
            result['content_valid'] = False
        
        if not has_content:
            result['structure_errors'].append("Missing content section")
            result['content_valid'] = False
        
        # Validate metadata block format
        if has_metadata:
            metadata_validation = self._validate_metadata_block_format(content)
            result['structure_errors'].extend(metadata_validation['errors'])
            result['structure_warnings'].extend(metadata_validation['warnings'])
        
        # Check for proper heading hierarchy
        heading_validation = self._validate_heading_hierarchy(content)
        result['structure_warnings'].extend(heading_validation)
        
        return result
    
    def _validate_content_quality(self, content: str) -> Dict[str, Any]:
        """Validate content quality."""
        result = {
            'content_valid': True,
            'quality_errors': [],
            'quality_warnings': [],
        }
        
        # Check minimum content length
        if len(content.strip()) < self.min_content_length:
            result['quality_errors'].append(f"Content too short: {len(content)} characters (minimum: {self.min_content_length})")
            result['content_valid'] = False
        
        # Check for empty content section
        content_section = self._extract_content_section(content)
        if not content_section or len(content_section.strip()) < 50:
            result['quality_errors'].append("Content section is empty or too short")
            result['content_valid'] = False
        
        # Check for excessive whitespace
        if re.search(r'\n\s*\n\s*\n\s*\n', content):
            result['quality_warnings'].append("Excessive blank lines detected")
        
        # Check for common OCR artifacts
        ocr_artifacts = ['|', '¦', '¦', '¦']
        for artifact in ocr_artifacts:
            if artifact in content:
                result['quality_warnings'].append(f"OCR artifact detected: '{artifact}'")
        
        return result
    
    def _validate_encoding(self, content: str) -> Dict[str, Any]:
        """Validate UTF-8 encoding."""
        result = {
            'encoding_valid': True,
            'encoding_errors': [],
        }
        
        try:
            # Try to encode and decode as UTF-8
            content.encode('utf-8').decode('utf-8')
        except UnicodeError as e:
            result['encoding_errors'].append(f"UTF-8 encoding error: {e}")
            result['encoding_valid'] = False
        
        return result
    
    def _validate_doc_id_format(self, doc_id: str) -> bool:
        """Validate document ID format."""
        # Pattern: number/year/letters/letters
        pattern = r'^\d{1,4}/\d{4}/[A-ZĐƠƯ\-]+/[A-ZĐƠƯ\-]+$'
        return bool(re.match(pattern, doc_id, re.IGNORECASE))
    
    def _validate_date_format(self, date: str) -> bool:
        """Validate date format (YYYY-MM-DD)."""
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date):
            return False
        
        # Check if it's a valid date
        try:
            from datetime import datetime
            datetime.strptime(date, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def _validate_category(self, category: str) -> bool:
        """Validate category value."""
        valid_categories = [
            'training_and_regulations',
            'decision',
            'policy',
            'announcement',
            'general_document'
        ]
        return category in valid_categories
    
    def _validate_metadata_block_format(self, content: str) -> Dict[str, List[str]]:
        """Validate metadata block format."""
        errors = []
        warnings = []
        
        lines = content.split('\n')
        in_metadata = False
        
        for line in lines:
            if line.strip() == '## Metadata':
                in_metadata = True
                continue
            elif line.startswith('## ') and in_metadata:
                break
            elif in_metadata and line.strip():
                if not line.strip().startswith('- **'):
                    errors.append(f"Invalid metadata line format: {line}")
                elif not line.strip().endswith(':'):
                    warnings.append(f"Metadata line should end with colon: {line}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_heading_hierarchy(self, content: str) -> List[str]:
        """Validate heading hierarchy."""
        warnings = []
        lines = content.split('\n')
        
        heading_levels = []
        for line in lines:
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_levels.append(level)
        
        # Check for skipped heading levels
        for i in range(1, len(heading_levels)):
            if heading_levels[i] > heading_levels[i-1] + 1:
                warnings.append(f"Heading level skipped: {heading_levels[i-1]} -> {heading_levels[i]}")
        
        return warnings
    
    def _extract_content_section(self, content: str) -> str:
        """Extract content section from markdown."""
        lines = content.split('\n')
        content_lines = []
        in_content = False
        
        for line in lines:
            if line.strip() == '## Nội dung':
                in_content = True
                continue
            elif line.startswith('## ') and in_content:
                break
            elif in_content:
                content_lines.append(line)
        
        return '\n'.join(content_lines)
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Get human-readable validation summary.
        
        Args:
            validation_result: Validation results dictionary
            
        Returns:
            Summary string
        """
        if validation_result['valid']:
            summary = "[OK] Document validation passed"
        else:
            summary = "[ERROR] Document validation failed"
        
        if validation_result.get('errors'):
            summary += f"\nErrors: {len(validation_result['errors'])}"
            for error in validation_result['errors'][:3]:  # Show first 3 errors
                summary += f"\n  - {error}"
        
        if validation_result.get('warnings'):
            summary += f"\nWarnings: {len(validation_result['warnings'])}"
            for warning in validation_result['warnings'][:3]:  # Show first 3 warnings
                summary += f"\n  - {warning}"
        
        return summary


def validate(markdown_content: str, metadata: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Convenience function to validate markdown document.
    
    Args:
        markdown_content: Markdown content to validate
        metadata: Optional metadata dictionary
        config: Optional configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    validator = DocumentValidator(config)
    result = validator.validate(markdown_content, metadata)
    return result['valid']
