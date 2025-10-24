"""
Celery tasks for Raw2MD Agent batch processing.

Provides async task processing with Redis backend for scalable document processing.
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

try:
    from celery import Celery  # type: ignore
except ImportError:
    # Fallback for environments where Celery is not available
    # This should not happen in production, but helps with IDE resolution
    Celery = None  # type: ignore

from .config import get_config
from .detector import detect_type, is_supported_format
from .extractors import get_extractor
from .cleaner import clean_text
from .metadata_agent import analyze_document
from .markdown_builder import build_metadata_block, compose_markdown
from .validator import validate
from .exporter import export_to_md

logger = logging.getLogger(__name__)

# Initialize Celery app
config = get_config()
if Celery is not None:
    celery_app = Celery(
        'raw2md_agent',
        broker=config.redis.url,
        backend=config.redis.url,
        include=['raw2md_agent.tasks']
    )
else:
    # Fallback for development/IDE environments
    celery_app = None

# Celery configuration
if celery_app is not None:
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minutes
        task_soft_time_limit=240,  # 4 minutes
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_disable_rate_limits=True,
    )


def celery_task(*args, **kwargs):
    """Decorator that handles Celery task creation with fallback."""
    if celery_app is not None:
        return celery_app.task(*args, **kwargs)
    else:
        # Return a no-op decorator for development/IDE environments
        def no_op_decorator(func):
            return func
        return no_op_decorator


class ProcessingResult:
    """Result of document processing."""
    
    def __init__(self, success: bool, file_path: str, output_path: Optional[str] = None, 
                 error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.file_path = file_path
        self.output_path = output_path
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'file_path': self.file_path,
            'output_path': self.output_path,
            'error': self.error,
            'metadata': self.metadata,
        }


@celery_task(bind=True, max_retries=3)
def process_single_file_task(self, file_path: str, output_dir: str = './output',
                           ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                           lang: str = 'vi', config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Celery task to process a single file.
    
    Args:
        file_path: Path to input file
        output_dir: Output directory
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config_dict: Configuration dictionary
        
    Returns:
        Processing result dictionary
    """
    try:
        logger.info(f"Processing file: {file_path} (task: {self.request.id})")
        
        # Process the file
        output_path = process_single_file_sync(
            file_path, output_dir, ocr_enabled, agent_mode, lang, config_dict
        )
        
        # Extract metadata for result
        metadata = {}
        try:
            # This is a simplified metadata extraction for the result
            metadata = {'status': 'completed', 'output_file': str(output_path)}
        except Exception as e:
            logger.warning(f"Could not extract metadata for result: {e}")
        
        result = ProcessingResult(
            success=True,
            file_path=file_path,
            output_path=str(output_path),
            metadata=metadata
        )
        
        logger.info(f"Successfully processed: {file_path}")
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {self.request.id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        # Final failure
        result = ProcessingResult(
            success=False,
            file_path=file_path,
            error=str(e)
        )
        return result.to_dict()


@celery_task(bind=True)
def process_batch_task(self, file_paths: List[str], output_dir: str = './output',
                      ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                      lang: str = 'vi', config_dict: Optional[Dict[str, Any]] = None,
                      batch_size: int = 10) -> Dict[str, Any]:
    """
    Celery task to process a batch of files.
    
    Args:
        file_paths: List of file paths to process
        output_dir: Output directory
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config_dict: Configuration dictionary
        batch_size: Number of files to process in parallel
        
    Returns:
        Batch processing results
    """
    logger.info(f"Processing batch of {len(file_paths)} files (task: {self.request.id})")
    
    results = []
    successful = 0
    failed = 0
    
    # Process files in batches
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i + batch_size]
        
        # Submit batch tasks
        batch_tasks = []
        for file_path in batch:
            task = process_single_file_task.delay(
                file_path, output_dir, ocr_enabled, agent_mode, lang, config_dict
            )
            batch_tasks.append(task)
        
        # Wait for batch completion
        for task in batch_tasks:
            try:
                result = task.get(timeout=300)  # 5 minute timeout per file
                results.append(result)
                
                if result['success']:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Batch task failed: {e}")
                failed += 1
                results.append({
                    'success': False,
                    'file_path': 'unknown',
                    'error': str(e)
                })
    
    logger.info(f"Batch processing completed: {successful} successful, {failed} failed")
    
    return {
        'total_files': len(file_paths),
        'successful': successful,
        'failed': failed,
        'results': results,
        'task_id': self.request.id,
    }


@celery_task
def process_directory_task(input_dir: str, output_dir: str = './output',
                         ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                         lang: str = 'vi', config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Celery task to process all files in a directory.
    
    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config_dict: Configuration dictionary
        
    Returns:
        Directory processing results
    """
    logger.info(f"Processing directory: {input_dir}")
    
    try:
        # Find all supported files
        input_path = Path(input_dir)
        if not input_path.exists() or not input_path.is_dir():
            raise ValueError(f"Directory not found: {input_dir}")
        
        supported_extensions = {'.pdf', '.docx', '.html', '.htm', '.txt', '.csv', 
                               '.xml', '.json', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp'}
        
        file_paths = []
        for ext in supported_extensions:
            file_paths.extend(input_path.glob(f'*{ext}'))
            file_paths.extend(input_path.glob(f'*{ext.upper()}'))
        
        if not file_paths:
            logger.warning(f"No supported files found in directory: {input_dir}")
            return {
                'total_files': 0,
                'successful': 0,
                'failed': 0,
                'results': [],
                'message': 'No supported files found'
            }
        
        # Process files using batch task
        file_path_strs = [str(fp) for fp in file_paths]
        batch_result = process_batch_task.delay(
            file_path_strs, output_dir, ocr_enabled, agent_mode, lang, config_dict
        )
        
        return batch_result.get()
        
    except Exception as e:
        logger.error(f"Directory processing failed: {e}")
        return {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'results': [],
            'error': str(e)
        }


def process_single_file_sync(file_path: str, output_dir: str = './output',
                           ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                           lang: str = 'vi', config_dict: Optional[Dict[str, Any]] = None) -> Path:
    """
    Synchronous file processing function for Celery tasks.
    
    Args:
        file_path: Path to input file
        output_dir: Output directory
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config_dict: Configuration dictionary
        
    Returns:
        Path to exported Markdown file
    """
    input_file = Path(file_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    # Detect file type
    file_type = detect_type(str(input_file))
    
    if not is_supported_format(file_type):
        logger.warning(f"Unsupported file type: {file_type}")
        file_type = 'unknown'
    
    # Prepare extractor configuration
    extractor_config = {
        'use_gpu': ocr_enabled,
        'lang': lang,
        'confidence_threshold': 0.6,
    }
    
    # Extract text
    extractor = get_extractor(file_type, str(input_file), extractor_config)
    raw_text = extractor.extract()
    
    if not raw_text or not raw_text.strip():
        raise ValueError("No text content extracted from file")
    
    # Clean text
    cleaned_text = clean_text(raw_text)
    
    # Extract metadata
    metadata = analyze_document(cleaned_text, config_dict, agent_mode)
    
    # Build markdown
    metadata_block = build_metadata_block(metadata)
    markdown_content = compose_markdown(metadata_block, cleaned_text, metadata)
    
    # Validate output
    is_valid = validate(markdown_content, metadata)
    if not is_valid:
        logger.warning("Output validation failed, but continuing...")
    
    # Export to file
    output_path = export_to_md(markdown_content, metadata, output_dir)
    
    return output_path


async def process_single_file_async(file_path: str, output_dir: str = './output',
                                 ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                                 lang: str = 'vi', config_dict: Optional[Dict[str, Any]] = None) -> Path:
    """
    Asynchronous file processing function.
    
    Args:
        file_path: Path to input file
        output_dir: Output directory
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config_dict: Configuration dictionary
        
    Returns:
        Path to exported Markdown file
    """
    # Run synchronous processing in thread pool
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(
            executor,
            process_single_file_sync,
            file_path, output_dir, ocr_enabled, agent_mode, lang, config_dict
        )
    
    return result


async def process_batch_async(file_paths: List[str], output_dir: str = './output',
                            ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                            lang: str = 'vi', config_dict: Optional[Dict[str, Any]] = None) -> List[Path]:
    """
    Asynchronous batch processing function.
    
    Args:
        file_paths: List of file paths to process
        output_dir: Output directory
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config_dict: Configuration dictionary
        
    Returns:
        List of exported file paths
    """
    tasks = []
    for file_path in file_paths:
        task = process_single_file_async(
            file_path, output_dir, ocr_enabled, agent_mode, lang, config_dict
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions and return successful results
    successful_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Failed to process {file_paths[i]}: {result}")
        else:
            successful_results.append(result)
    
    return successful_results


# Celery worker configuration
@celery_task
def health_check() -> Dict[str, str]:
    """Health check task for monitoring."""
    return {
        'status': 'healthy',
        'timestamp': str(asyncio.get_event_loop().time()),
        'worker': 'raw2md_agent'
    }


@celery_task
def get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics."""
    if celery_app is None:
        return {'error': 'Celery not available'}
    
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        
        return {
            'stats': stats,
            'active': active,
            'queues': list(celery_app.conf.task_routes.keys()) if celery_app.conf.task_routes else []
        }
    except Exception as e:
        return {'error': str(e)}


# Export Celery app for external use
__all__ = [
    'celery_app',
    'process_single_file_task',
    'process_batch_task',
    'process_directory_task',
    'process_single_file_sync',
    'process_single_file_async',
    'process_batch_async',
    'health_check',
    'get_queue_stats',
]
