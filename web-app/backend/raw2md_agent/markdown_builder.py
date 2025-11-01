"""
Markdown builder for Raw2MD Agent.

Builds clean Markdown files with metadata blocks and formatted content.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MarkdownBuilder:
    """
    Markdown builder for creating structured documents.
    
    Features:
    - Metadata block formatting
    - Content composition
    - Vietnamese document structure
    - Clean formatting
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize markdown builder.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.metadata_template = self.config.get('metadata_template', 'standard')
    
    def build_metadata_block(self, metadata: Dict[str, Any]) -> str:
        """
        Build metadata block in Markdown format.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Formatted metadata block
        """
        if not metadata:
            return ""
        
        lines = ["## Metadata"]
        
        # Define field order and labels
        field_order = [
            ('doc_id', 'doc_id'),
            ('category', 'category'),
            ('source', 'source'),
            ('date', 'date'),
            ('modify', 'modify'),
            ('partial_mod', 'partial_mod'),
            ('data_type', 'data_type'),
            ('amend', 'amend'),
        ]
        
        for field_key, field_label in field_order:
            value = metadata.get(field_key, '')
            
            # Format boolean values
            if isinstance(value, bool):
                value = str(value)
            
            # Skip empty values for optional fields
            if not value and field_key in ['modify', 'amend']:
                continue
            
            lines.append(f"- **{field_label}:** {value}")
        
        return '\n'.join(lines)
    
    def compose_markdown(self, metadata_block: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Compose complete Markdown document.
        
        Args:
            metadata_block: Formatted metadata block
            text: Cleaned text content
            metadata: Optional metadata dictionary for title generation
            
        Returns:
            Complete Markdown document
        """
        if not text or not text.strip():
            raise ValueError("Text content cannot be empty")
        
        # Build the complete document
        document_parts = []
        
        # Add document title if metadata is available
        if metadata:
            title = self.format_document_title(metadata)
            document_parts.append(f"# {title}")
            document_parts.append("")
        
        # Add metadata block
        if metadata_block:
            document_parts.append(metadata_block)
            document_parts.append("")  # Empty line
        
        # Add content section
        document_parts.append("## Nội dung")
        document_parts.append("")
        document_parts.append(text.strip())
        
        return '\n'.join(document_parts)
    
    def format_document_title(self, metadata: Dict[str, Any]) -> str:
        """
        Format document title from metadata.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Formatted title
        """
        source = metadata.get('source', '')
        doc_id = metadata.get('doc_id', '')
        
        if source:
            return source
        elif doc_id:
            return f"Tài liệu {doc_id}"
        else:
            return "Tài liệu không có tiêu đề"
    
    def add_document_header(self, markdown_content: str, metadata: Dict[str, Any]) -> str:
        """
        Add document header to markdown content.
        
        Args:
            markdown_content: Existing markdown content
            metadata: Metadata dictionary
            
        Returns:
            Markdown content with header
        """
        title = self.format_document_title(metadata)
        
        header_lines = [
            f"# {title}",
            "",
        ]
        
        return '\n'.join(header_lines) + '\n' + markdown_content
    
    def format_table_of_contents(self, text: str) -> str:
        """
        Generate table of contents from text headings.
        
        Args:
            text: Markdown text content
            
        Returns:
            Table of contents
        """
        import re
        
        lines = text.split('\n')
        toc_lines = ["## Mục lục", ""]
        
        for line in lines:
            line = line.strip()
            
            # Match headings
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_text = line.lstrip('#').strip()
                
                if heading_text:
                    # Create anchor link
                    anchor = heading_text.lower().replace(' ', '-').replace('.', '')
                    anchor = re.sub(r'[^\w\-]', '', anchor)
                    
                    indent = '  ' * (level - 1)
                    toc_lines.append(f"{indent}- [{heading_text}](#{anchor})")
        
        if len(toc_lines) > 2:  # More than just the header
            return '\n'.join(toc_lines) + '\n'
        
        return ""
    
    def enhance_document_structure(self, markdown_content: str, metadata: Dict[str, Any]) -> str:
        """
        Enhance document structure with additional formatting.
        
        Args:
            markdown_content: Base markdown content
            metadata: Metadata dictionary
            
        Returns:
            Enhanced markdown content
        """
        enhanced_parts = []
        
        # Add document header
        enhanced_content = self.add_document_header(markdown_content, metadata)
        
        # Split into sections
        sections = enhanced_content.split('\n## ')
        
        if len(sections) > 1:
            # Reconstruct with proper section headers
            enhanced_parts.append(sections[0])  # Header and metadata
            
            for section in sections[1:]:
                if section.strip():
                    enhanced_parts.append("## " + section)
        else:
            enhanced_parts.append(enhanced_content)
        
        return '\n\n'.join(enhanced_parts)
    
    def validate_markdown(self, markdown_content: str) -> Dict[str, Any]:
        """
        Validate markdown content structure.
        
        Args:
            markdown_content: Markdown content to validate
            
        Returns:
            Validation results dictionary
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        lines = markdown_content.split('\n')
        
        # Check for required sections
        has_metadata = '## Metadata' in markdown_content
        has_content = '## Nội dung' in markdown_content
        
        if not has_metadata:
            validation_result['errors'].append("Missing metadata section")
            validation_result['valid'] = False
        
        if not has_content:
            validation_result['errors'].append("Missing content section")
            validation_result['valid'] = False
        
        # Check metadata format
        if has_metadata:
            metadata_lines = []
            in_metadata = False
            
            for line in lines:
                if line.strip() == '## Metadata':
                    in_metadata = True
                    continue
                elif line.startswith('## ') and in_metadata:
                    break
                elif in_metadata and line.strip():
                    metadata_lines.append(line)
            
            # Validate metadata format
            for line in metadata_lines:
                if not line.strip().startswith('- **'):
                    validation_result['warnings'].append(f"Invalid metadata line format: {line}")
        
        # Calculate statistics
        validation_result['stats'] = {
            'total_lines': len(lines),
            'non_empty_lines': len([line for line in lines if line.strip()]),
            'total_characters': len(markdown_content),
            'has_metadata': has_metadata,
            'has_content': has_content,
        }
        
        return validation_result


def build_metadata_block(metadata: Dict[str, Any]) -> str:
    """
    Convenience function to build metadata block.
    
    Args:
        metadata: Metadata dictionary
        
    Returns:
        Formatted metadata block
    """
    builder = MarkdownBuilder()
    return builder.build_metadata_block(metadata)


def compose_markdown(metadata_block: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Convenience function to compose markdown document.
    
    Args:
        metadata_block: Formatted metadata block
        text: Cleaned text content
        metadata: Optional metadata dictionary for title generation
        
    Returns:
        Complete Markdown document
    """
    builder = MarkdownBuilder()
    return builder.compose_markdown(metadata_block, text, metadata)
