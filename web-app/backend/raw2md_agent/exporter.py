"""
File exporter for Raw2MD Agent.

Handles safe file naming, UTF-8 encoding, and output directory management.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentExporter:
    """
    Document exporter for markdown files.
    
    Features:
    - Safe filename generation
    - UTF-8 encoding
    - Output directory management
    - File conflict resolution
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize document exporter.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.output_dir = Path(self.config.get('output_dir', './output'))
        self.filename_template = self.config.get('filename_template', '{doc_id}__{category}__{date}')
        self.ensure_output_dir = self.config.get('ensure_output_dir', True)
        
        if self.ensure_output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_md(self, markdown_content: str, metadata: Dict[str, Any], 
                     custom_filename: Optional[str] = None) -> Path:
        """
        Export markdown content to file.
        
        Args:
            markdown_content: Markdown content to export
            metadata: Metadata dictionary
            custom_filename: Optional custom filename
            
        Returns:
            Path to exported file
            
        Raises:
            ValueError: If metadata is insufficient for filename generation
            IOError: If file writing fails
        """
        if not markdown_content or not markdown_content.strip():
            raise ValueError("Markdown content cannot be empty")
        
        # Generate filename
        if custom_filename:
            filename = custom_filename
        else:
            filename = self._generate_filename(metadata)
        
        # Ensure .md extension
        if not filename.endswith('.md'):
            filename += '.md'
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        # Resolve file path
        file_path = self.output_dir / safe_filename
        
        # Handle file conflicts
        file_path = self._resolve_file_conflict(file_path)
        
        # Write file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Successfully exported document to: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            raise IOError(f"Failed to write file: {e}")
    
    def _generate_filename(self, metadata: Dict[str, Any]) -> str:
        """
        Generate filename from metadata.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Generated filename
        """
        # Extract required fields
        doc_id = metadata.get('doc_id', '')
        category = metadata.get('category', 'general_document')
        date = metadata.get('date', '')
        
        # Handle missing doc_id
        if not doc_id:
            # Try to extract from source
            source = metadata.get('source', '')
            if source:
                # Extract first few words from source
                words = source.split()[:3]
                doc_id = '_'.join(words)
            else:
                doc_id = 'unknown_document'
        
        # Handle missing date
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Generate filename using template
        filename = self.filename_template.format(
            doc_id=self._sanitize_component(doc_id),
            category=self._sanitize_component(category),
            date=self._sanitize_component(date)
        )
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe filesystem usage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        # Ensure not empty
        if not filename:
            filename = 'document'
        
        return filename
    
    def _sanitize_component(self, component: str) -> str:
        """
        Sanitize a filename component.
        
        Args:
            component: Component to sanitize
            
        Returns:
            Sanitized component
        """
        if not component:
            return 'unknown'
        
        # Replace spaces and special characters
        component = re.sub(r'[\s\-/\\]', '_', component)
        
        # Remove multiple underscores
        component = re.sub(r'_+', '_', component)
        
        # Remove leading/trailing underscores
        component = component.strip('_')
        
        return component
    
    def _resolve_file_conflict(self, file_path: Path) -> Path:
        """
        Resolve file naming conflicts.
        
        Args:
            file_path: Original file path
            
        Returns:
            Resolved file path
        """
        if not file_path.exists():
            return file_path
        
        # Add counter suffix
        counter = 1
        while True:
            stem = file_path.stem
            suffix = file_path.suffix
            new_path = file_path.parent / f"{stem}_{counter}{suffix}"
            
            if not new_path.exists():
                logger.info(f"File conflict resolved: {file_path} -> {new_path}")
                return new_path
            
            counter += 1
            
            # Prevent infinite loop
            if counter > 1000:
                logger.warning(f"Too many file conflicts for {file_path}")
                break
        
        # Fallback: add timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stem = file_path.stem
        suffix = file_path.suffix
        return file_path.parent / f"{stem}_{timestamp}{suffix}"
    
    def export_batch(self, documents: list, metadata_list: list) -> list:
        """
        Export multiple documents in batch.
        
        Args:
            documents: List of markdown content strings
            metadata_list: List of metadata dictionaries
            
        Returns:
            List of exported file paths
        """
        if len(documents) != len(metadata_list):
            raise ValueError("Documents and metadata lists must have same length")
        
        exported_paths = []
        
        for i, (doc, metadata) in enumerate(zip(documents, metadata_list)):
            try:
                # Add index to filename to avoid conflicts
                custom_filename = f"batch_{i+1:03d}"
                path = self.export_to_md(doc, metadata, custom_filename)
                exported_paths.append(path)
                
            except Exception as e:
                logger.error(f"Failed to export document {i+1}: {e}")
                exported_paths.append(None)
        
        return exported_paths
    
    def get_output_stats(self) -> Dict[str, Any]:
        """
        Get output directory statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.output_dir.exists():
            return {'exists': False, 'file_count': 0, 'total_size': 0}
        
        files = list(self.output_dir.glob('*.md'))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            'exists': True,
            'file_count': len(files),
            'total_size': total_size,
            'output_dir': str(self.output_dir.absolute()),
        }
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """
        Clean up old files from output directory.
        
        Args:
            days_old: Files older than this many days will be deleted
            
        Returns:
            Number of files deleted
        """
        if not self.output_dir.exists():
            return 0
        
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        deleted_count = 0
        
        for file_path in self.output_dir.glob('*.md'):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
        
        return deleted_count


def export_to_md(markdown_content: str, metadata: Dict[str, Any], 
                 output_dir: Union[str, Path] = './output', 
                 custom_filename: Optional[str] = None) -> Path:
    """
    Convenience function to export markdown document.
    
    Args:
        markdown_content: Markdown content to export
        metadata: Metadata dictionary
        output_dir: Output directory path
        custom_filename: Optional custom filename
        
    Returns:
        Path to exported file
    """
    config = {'output_dir': str(output_dir)}
    exporter = DocumentExporter(config)
    return exporter.export_to_md(markdown_content, metadata, custom_filename)
