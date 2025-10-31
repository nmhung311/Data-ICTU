"""
Ray distributed pipeline for Raw2MD Agent.

Provides massive-scale document processing using Ray for distributed computing.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import ray  # type: ignore
except ImportError:
    # Fallback for environments where Ray is not available
    ray = None  # type: ignore

from .config import get_config
from .detector import detect_type, is_supported_format
from .extractors import get_extractor
from .cleaner import clean_text
from .metadata_agent import analyze_document
from .markdown_builder import build_metadata_block, compose_markdown
from .validator import validate
from .exporter import export_to_md

logger = logging.getLogger(__name__)

# Initialize Ray
config = get_config()

# Ray configuration
RAY_CONFIG = {
    'address': config.ray.address,
    'num_cpus': config.ray.num_cpus,
    'num_gpus': config.ray.num_gpus,
    'object_store_memory': 2 * 1024 * 1024 * 1024,  # 2GB
    'ignore_reinit_error': True,
} if ray is not None else {}


class ProcessingResult:
    """Result of document processing."""
    
    def __init__(self, success: bool, file_path: str, output_path: Optional[str] = None,
                 error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
                 processing_time: Optional[float] = None):
        self.success = success
        self.file_path = file_path
        self.output_path = output_path
        self.error = error
        self.metadata = metadata or {}
        self.processing_time = processing_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'file_path': self.file_path,
            'output_path': self.output_path,
            'error': self.error,
            'metadata': self.metadata,
            'processing_time': self.processing_time,
        }


def ray_remote(*args, **kwargs):
    """Decorator that handles Ray remote creation with fallback."""
    if ray is not None:
        return ray.remote(*args, **kwargs)
    else:
        # Return a no-op decorator for development/IDE environments
        def no_op_decorator(func):
            return func
        return no_op_decorator


@ray_remote
class DocumentProcessor:
    """Ray actor for document processing."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize document processor actor.
        
        Args:
            config_dict: Configuration dictionary
        """
        self.config = config_dict or {}
        self.processed_count = 0
        self.error_count = 0
    
    def process_single_file(self, file_path: str, output_dir: str = './output',
                          ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                          lang: str = 'vi') -> Dict[str, Any]:
        """
        Process a single file.
        
        Args:
            file_path: Path to input file
            output_dir: Output directory
            ocr_enabled: Enable OCR processing
            agent_mode: Metadata extraction mode
            lang: Language code
            
        Returns:
            Processing result dictionary
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Processing file: {file_path}")
            
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
            metadata = analyze_document(cleaned_text, self.config, agent_mode)
            
            # Build markdown
            metadata_block = build_metadata_block(metadata)
            markdown_content = compose_markdown(metadata_block, cleaned_text, metadata)
            
            # Validate output
            is_valid = validate(markdown_content, metadata)
            if not is_valid:
                logger.warning("Output validation failed, but continuing...")
            
            # Export to file
            output_path = export_to_md(markdown_content, metadata, output_dir)
            
            processing_time = time.time() - start_time
            self.processed_count += 1
            
            result = ProcessingResult(
                success=True,
                file_path=file_path,
                output_path=str(output_path),
                metadata=metadata,
                processing_time=processing_time
            )
            
            logger.info(f"Successfully processed: {file_path} in {processing_time:.2f}s")
            return result.to_dict()
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.error_count += 1
            
            logger.error(f"Failed to process {file_path}: {e}")
            
            result = ProcessingResult(
                success=False,
                file_path=file_path,
                error=str(e),
                processing_time=processing_time
            )
            
            return result.to_dict()
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
        }


@ray_remote
def process_file_chunk(file_paths: List[str], output_dir: str = './output',
                      ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                      lang: str = 'vi', config_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Process a chunk of files.
    
    Args:
        file_paths: List of file paths to process
        output_dir: Output directory
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config_dict: Configuration dictionary
        
    Returns:
        List of processing results
    """
    processor = DocumentProcessor.remote(config_dict) if ray is not None else DocumentProcessor(config_dict)  # type: ignore
    results = []
    
    for file_path in file_paths:
        if ray is not None:
            result = ray.get(processor.process_single_file.remote(  # type: ignore
                file_path, output_dir, ocr_enabled, agent_mode, lang
            ))
        else:
            result = processor.process_single_file(
                file_path, output_dir, ocr_enabled, agent_mode, lang
            )
        results.append(result)
    
    return results


class RayPipeline:
    """
    Ray-based distributed processing pipeline.
    
    Features:
    - Distributed document processing
    - Dynamic scaling
    - Progress tracking
    - Error handling and recovery
    """
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize Ray pipeline.
        
        Args:
            config_dict: Configuration dictionary
        """
        self.config = config_dict or {}
        self.processors = []
        self.is_initialized = False
    
    def initialize(self) -> None:
        """Initialize Ray cluster."""
        if self.is_initialized:
            return
        
        if ray is None:
            logger.warning("Ray is not available, running in single-threaded mode")
            self.is_initialized = True
            return
        
        try:
            # Initialize Ray
            ray.init(**RAY_CONFIG)
            logger.info("Ray cluster initialized successfully")
            
            # Create processor actors
            num_processors = self.config.get('num_processors', 4)
            self.processors = [
                DocumentProcessor.remote(self.config)  # type: ignore
                for _ in range(num_processors)
            ]
            
            self.is_initialized = True
            logger.info(f"Created {num_processors} processor actors")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ray cluster: {e}")
            raise
    
    def shutdown(self) -> None:
        """Shutdown Ray cluster."""
        if self.is_initialized and ray is not None:
            ray.shutdown()
            self.is_initialized = False
            logger.info("Ray cluster shutdown")
    
    def process_files(self, file_paths: List[str], output_dir: str = './output',
                     ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                     lang: str = 'vi', chunk_size: int = 10) -> List[Dict[str, Any]]:
        """
        Process files using Ray distributed computing.
        
        Args:
            file_paths: List of file paths to process
            output_dir: Output directory
            ocr_enabled: Enable OCR processing
            agent_mode: Metadata extraction mode
            lang: Language code
            chunk_size: Number of files per chunk
            
        Returns:
            List of processing results
        """
        if not self.is_initialized:
            self.initialize()
        
        logger.info(f"Processing {len(file_paths)} files using Ray pipeline")
        
        if ray is None:
            # Fallback to sequential processing
            logger.info("Ray not available, processing files sequentially")
            results = []
            for file_path in file_paths:
                try:
                    # Create a temporary processor for sequential processing
                    processor = DocumentProcessor()
                    result = processor.process_single_file(file_path, output_dir, ocr_enabled, agent_mode, lang)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    results.append({
                        'success': False,
                        'file_path': file_path,
                        'error': str(e)
                    })
            return results
        
        # Split files into chunks
        chunks = [file_paths[i:i + chunk_size] for i in range(0, len(file_paths), chunk_size)]
        
        # Submit chunks to Ray
        futures = []
        for chunk in chunks:
            future = process_file_chunk.remote(
                chunk, output_dir, ocr_enabled, agent_mode, lang, self.config
            )
            futures.append(future)
        
        # Collect results
        all_results = []
        successful = 0
        failed = 0
        
        for i, future in enumerate(futures):
            try:
                chunk_results = ray.get(future)
                all_results.extend(chunk_results)
                
                # Count successes and failures
                for result in chunk_results:
                    if result['success']:
                        successful += 1
                    else:
                        failed += 1
                
                logger.info(f"Completed chunk {i+1}/{len(chunks)}")
                
            except Exception as e:
                logger.error(f"Chunk {i+1} failed: {e}")
                failed += len(chunks[i])
        
        logger.info(f"Ray processing completed: {successful} successful, {failed} failed")
        
        return all_results
    
    def process_directory(self, input_dir: str, output_dir: str = './output',
                        ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                        lang: str = 'vi', chunk_size: int = 10) -> Dict[str, Any]:
        """
        Process all files in a directory using Ray.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            ocr_enabled: Enable OCR processing
            agent_mode: Metadata extraction mode
            lang: Language code
            chunk_size: Number of files per chunk
            
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
            
            # Process files
            file_path_strs = [str(fp) for fp in file_paths]
            results = self.process_files(
                file_path_strs, output_dir, ocr_enabled, agent_mode, lang, chunk_size
            )
            
            # Calculate statistics
            successful = len([r for r in results if r['success']])
            failed = len(results) - successful
            
            return {
                'total_files': len(file_paths),
                'successful': successful,
                'failed': failed,
                'results': results,
            }
            
        except Exception as e:
            logger.error(f"Directory processing failed: {e}")
            return {
                'total_files': 0,
                'successful': 0,
                'failed': 0,
                'results': [],
                'error': str(e)
            }
    
    def get_cluster_stats(self) -> Dict[str, Any]:
        """Get Ray cluster statistics."""
        if not self.is_initialized:
            return {'error': 'Ray cluster not initialized'}
        
        if ray is None:
            return {'error': 'Ray not available'}
        
        try:
            # Get cluster resources
            resources = ray.cluster_resources()
            
            # Get processor statistics
            processor_stats = []
            for processor in self.processors:
                stats = ray.get(processor.get_stats.remote())
                processor_stats.append(stats)
            
            return {
                'cluster_resources': resources,
                'processor_stats': processor_stats,
                'num_processors': len(self.processors),
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def scale_processors(self, num_processors: int) -> None:
        """
        Scale the number of processor actors.
        
        Args:
            num_processors: New number of processors
        """
        if not self.is_initialized:
            self.initialize()
        
        current_count = len(self.processors)
        
        if num_processors > current_count:
            # Add more processors
            new_processors = [
                DocumentProcessor.remote(self.config)  # type: ignore
                for _ in range(num_processors - current_count)
            ]
            self.processors.extend(new_processors)
            logger.info(f"Scaled up to {num_processors} processors")
            
        elif num_processors < current_count:
            # Remove processors
            self.processors = self.processors[:num_processors]
            logger.info(f"Scaled down to {num_processors} processors")
    
    def process_large_document(self, file_path: str, output_dir: str = './output',
                             ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                             lang: str = 'vi', chunk_size_mb: int = 2) -> Dict[str, Any]:
        """
        Process a large document by splitting it into chunks.
        
        Args:
            file_path: Path to large document
            output_dir: Output directory
            ocr_enabled: Enable OCR processing
            agent_mode: Metadata extraction mode
            lang: Language code
            chunk_size_mb: Chunk size in MB
            
        Returns:
            Processing result
        """
        logger.info(f"Processing large document: {file_path}")
        
        try:
            # For now, process as single file
            # In a full implementation, this would split large documents
            results = self.process_files([file_path], output_dir, ocr_enabled, agent_mode, lang)
            
            if results:
                return results[0]
            else:
                return {
                    'success': False,
                    'file_path': file_path,
                    'error': 'No results returned'
                }
                
        except Exception as e:
            logger.error(f"Large document processing failed: {e}")
            return {
                'success': False,
                'file_path': file_path,
                'error': str(e)
            }


# Convenience functions
def initialize_ray_pipeline(config_dict: Optional[Dict[str, Any]] = None) -> RayPipeline:
    """
    Initialize Ray pipeline.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        Initialized Ray pipeline
    """
    pipeline = RayPipeline(config_dict)
    pipeline.initialize()
    return pipeline


def process_files_distributed(file_paths: List[str], output_dir: str = './output',
                            ocr_enabled: bool = True, agent_mode: str = 'hybrid',
                            lang: str = 'vi', config_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Process files using Ray distributed computing.
    
    Args:
        file_paths: List of file paths to process
        output_dir: Output directory
        ocr_enabled: Enable OCR processing
        agent_mode: Metadata extraction mode
        lang: Language code
        config_dict: Configuration dictionary
        
    Returns:
        List of processing results
    """
    pipeline = initialize_ray_pipeline(config_dict)
    
    try:
        results = pipeline.process_files(file_paths, output_dir, ocr_enabled, agent_mode, lang)
        return results
    finally:
        pipeline.shutdown()


# Export main classes and functions
__all__ = [
    'RayPipeline',
    'DocumentProcessor',
    'ProcessingResult',
    'initialize_ray_pipeline',
    'process_files_distributed',
    'process_file_chunk',
]
