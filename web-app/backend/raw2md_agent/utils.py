"""
Utility functions for Raw2MD Agent.

Common helper functions used across the application.
"""

import logging
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Union
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)


def generate_file_hash(file_path: Union[str, Path], algorithm: str = 'md5') -> str:
    """
    Generate hash for a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        File hash as hexadecimal string
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for safe filesystem usage.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename
    """
    import re
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = max_length - len(ext) - 1 if ext else max_length
        filename = name[:max_name_length] + ('.' + ext if ext else '')
    
    # Ensure not empty
    if not filename:
        filename = 'unnamed_file'
    
    return filename


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024.0 and i < len(size_names) - 1:
        size_float /= 1024.0
        i += 1
    
    return f"{size_float:.1f} {size_names[i]}"


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get comprehensive file information.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {'exists': False}
    
    stat = file_path.stat()
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    
    return {
        'exists': True,
        'path': str(file_path.absolute()),
        'name': file_path.name,
        'stem': file_path.stem,
        'suffix': file_path.suffix,
        'size_bytes': stat.st_size,
        'size_formatted': format_file_size(stat.st_size),
        'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'accessed_time': datetime.fromtimestamp(stat.st_atime).isoformat(),
        'mime_type': mime_type,
        'is_file': file_path.is_file(),
        'is_dir': file_path.is_dir(),
    }


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Read JSON file safely.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json_file(data: Dict[str, Any], file_path: Union[str, Path], 
                   indent: int = 2, ensure_ascii: bool = False) -> None:
    """
    Write data to JSON file safely.
    
    Args:
        data: Data to write
        file_path: Path to JSON file
        indent: JSON indentation
        ensure_ascii: Ensure ASCII encoding
        
    Raises:
        IOError: If file cannot be written
    """
    file_path = Path(file_path)
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks of specified size.
    
    Args:
        items: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0, 
                      backoff_factor: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds
        backoff_factor: Backoff multiplication factor
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    import time
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            
            if attempt == max_retries:
                break
            
            delay = base_delay * (backoff_factor ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
    
    if last_exception is not None:
        raise last_exception
    else:
        raise RuntimeError("Retry function failed without catching any exceptions")


def validate_file_path(file_path: Union[str, Path], must_exist: bool = True) -> Path:
    """
    Validate and normalize file path.
    
    Args:
        file_path: File path to validate
        must_exist: Whether file must exist
        
    Returns:
        Normalized Path object
        
    Raises:
        ValueError: If path is invalid
        FileNotFoundError: If file doesn't exist and must_exist is True
    """
    path = Path(file_path)
    
    if not path:
        raise ValueError("File path cannot be empty")
    
    if must_exist and not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    return path.resolve()


def get_supported_file_extensions() -> Dict[str, List[str]]:
    """
    Get supported file extensions by category.
    
    Returns:
        Dictionary mapping categories to file extensions
    """
    return {
        'documents': ['.pdf', '.docx', '.doc', '.rtf'],
        'web': ['.html', '.htm', '.xhtml'],
        'text': ['.txt', '.md', '.rst'],
        'data': ['.csv', '.tsv', '.json', '.xml'],
        'images': ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp', '.gif'],
        'all': ['.pdf', '.docx', '.doc', '.rtf', '.html', '.htm', '.xhtml', 
                '.txt', '.md', '.rst', '.csv', '.tsv', '.json', '.xml',
                '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp', '.gif']
    }


def create_progress_bar(total: int, description: str = "Processing") -> Any:
    """
    Create a progress bar for long-running operations.
    
    Args:
        total: Total number of items
        description: Description for the progress bar
        
    Returns:
        Progress bar object
    """
    try:
        from tqdm import tqdm
        return tqdm(total=total, desc=description, unit="files")
    except ImportError:
        logger.warning("tqdm not available, using simple progress tracking")
        return None


def log_processing_stats(stats: Dict[str, Any]) -> None:
    """
    Log processing statistics in a formatted way.
    
    Args:
        stats: Statistics dictionary
    """
    logger.info("=== Processing Statistics ===")
    
    for key, value in stats.items():
        if isinstance(value, dict):
            logger.info(f"{key}:")
            for sub_key, sub_value in value.items():
                logger.info(f"  {sub_key}: {sub_value}")
        else:
            logger.info(f"{key}: {value}")
    
    logger.info("=============================")


def cleanup_temp_files(temp_dir: Union[str, Path], max_age_hours: int = 24) -> int:
    """
    Clean up temporary files older than specified age.
    
    Args:
        temp_dir: Temporary directory path
        max_age_hours: Maximum age in hours
        
    Returns:
        Number of files deleted
    """
    temp_path = Path(temp_dir)
    
    if not temp_path.exists():
        return 0
    
    cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
    deleted_count = 0
    
    for file_path in temp_path.rglob('*'):
        if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
            try:
                file_path.unlink()
                deleted_count += 1
                logger.debug(f"Deleted temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {file_path}: {e}")
    
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} temporary files")
    
    return deleted_count


def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage statistics.
    
    Returns:
        Dictionary with memory usage in MB
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': process.memory_percent(),
        }
    except ImportError:
        logger.warning("psutil not available, cannot get memory usage")
        return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0}


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"
