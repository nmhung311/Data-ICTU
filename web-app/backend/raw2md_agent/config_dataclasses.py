"""
Configuration management for Raw2MD Agent using Dataclasses.

Handles environment variables, default settings, and validation
for all processing modes (simple, batch, distributed).
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field
# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not available. Environment variables will not be loaded from .env file")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")


@dataclass
class ProcessingConfig:
    """Processing mode and performance settings."""
    
    mode: str = "simple"
    batch_size: int = 32
    concurrency: int = 8
    max_retries: int = 3
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.mode not in ['simple', 'batch', 'distributed']:
            raise ValueError('Mode must be one of: simple, batch, distributed')
        if not (1 <= self.batch_size <= 100):
            raise ValueError('Batch size must be between 1 and 100')
        if not (1 <= self.concurrency <= 32):
            raise ValueError('Concurrency must be between 1 and 32')
        if not (0 <= self.max_retries <= 10):
            raise ValueError('Max retries must be between 0 and 10')


@dataclass
class RedisConfig:
    """Redis configuration for caching and message broker."""
    
    url: str = "redis://localhost:6379/0"
    cache_ttl: int = 2592000  # 30 days
    enabled: bool = True


@dataclass
class MinIOConfig:
    """MinIO/S3 storage configuration."""
    
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin123"
    bucket_name: str = "raw2md-documents"
    secure: bool = False


@dataclass
class LLMConfig:
    """Gemini 2.5 Flash LLM configuration."""
    
    api_key: Optional[str] = None
    model: str = "gemini-2.5-flash"
    temperature: float = 0.0
    max_tokens: int = 500
    timeout: int = 30
    
    def __post_init__(self):
        """Validate LLM configuration."""
        if self.api_key is None or self.api_key == "your_google_api_key_here":
            logging.warning("Google API key not configured. LLM mode will be disabled.")
        if not (0.0 <= self.temperature <= 1.0):
            raise ValueError('Temperature must be between 0.0 and 1.0')
        if not (100 <= self.max_tokens <= 2000):
            raise ValueError('Max tokens must be between 100 and 2000')
        if not (5 <= self.timeout <= 120):
            raise ValueError('Timeout must be between 5 and 120 seconds')


@dataclass
class OCRConfig:
    """OCR configuration for document processing."""
    
    use_gpu: bool = True
    lang: str = "vie+eng"
    confidence_threshold: float = 0.5
    tesseract_path: str = "/usr/bin/tesseract"
    tesseract_config: str = "--psm 6 --oem 3"
    image_dpi: int = 300
    image_scale: float = 2.0
    enable_preprocessing: bool = True
    denoise_enabled: bool = True
    contrast_enhancement: bool = True
    deskew_enabled: bool = True
    
    def __post_init__(self):
        """Validate OCR configuration."""
        if not (0.0 <= self.confidence_threshold <= 1.0):
            raise ValueError('Confidence threshold must be between 0.0 and 1.0')
        if not (150 <= self.image_dpi <= 600):
            raise ValueError('Image DPI must be between 150 and 600')
        if not (1.0 <= self.image_scale <= 4.0):
            raise ValueError('Image scale must be between 1.0 and 4.0')


@dataclass
class FileConfig:
    """File handling configuration."""
    
    input_dir: str = "./input"
    output_dir: str = "./output"
    temp_dir: str = "./temp"
    max_file_size_mb: int = 100
    supported_formats: List[str] = field(default_factory=lambda: [
        "pdf", "docx", "html", "txt", "csv", "xml", "json", 
        "jpg", "jpeg", "png", "tiff", "bmp", "webp"
    ])
    
    def __post_init__(self):
        """Validate file configuration."""
        if not (1 <= self.max_file_size_mb <= 1000):
            raise ValueError('Max file size must be between 1 and 1000 MB')


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    level: str = "INFO"
    format: str = "json"
    file: Optional[str] = None
    
    def __post_init__(self):
        """Validate logging configuration."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.level.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        self.level = self.level.upper()
        
        if self.format not in ['json', 'text']:
            raise ValueError('Log format must be either "json" or "text"')


@dataclass
class PerformanceConfig:
    """Performance and optimization settings."""
    
    async_io_workers: int = 10
    ocr_batch_size: int = 8
    llm_batch_size: int = 5
    cache_enabled: bool = True
    metrics_enabled: bool = True
    
    def __post_init__(self):
        """Validate performance configuration."""
        if not (1 <= self.async_io_workers <= 50):
            raise ValueError('Async I/O workers must be between 1 and 50')
        if not (1 <= self.ocr_batch_size <= 32):
            raise ValueError('OCR batch size must be between 1 and 32')
        if not (1 <= self.llm_batch_size <= 20):
            raise ValueError('LLM batch size must be between 1 and 20')


@dataclass
class RayConfig:
    """Ray distributed computing configuration."""
    
    address: str = "ray://localhost:10001"
    num_cpus: int = 8
    num_gpus: int = 1
    
    def __post_init__(self):
        """Validate Ray configuration."""
        if not (1 <= self.num_cpus <= 64):
            raise ValueError('Number of CPUs must be between 1 and 64')
        if not (0 <= self.num_gpus <= 8):
            raise ValueError('Number of GPUs must be between 0 and 8')


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    
    prometheus_port: int = 8000
    flower_port: int = 5555
    health_check_interval: int = 30
    
    def __post_init__(self):
        """Validate monitoring configuration."""
        if not (1000 <= self.prometheus_port <= 65535):
            raise ValueError('Prometheus port must be between 1000 and 65535')
        if not (1000 <= self.flower_port <= 65535):
            raise ValueError('Flower port must be between 1000 and 65535')
        if not (5 <= self.health_check_interval <= 300):
            raise ValueError('Health check interval must be between 5 and 300 seconds')


@dataclass
class Config:
    """Main configuration class combining all settings."""
    
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    minio: MinIOConfig = field(default_factory=MinIOConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    files: FileConfig = field(default_factory=FileConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    ray: RayConfig = field(default_factory=RayConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables."""
        return cls(
            processing=ProcessingConfig(
                mode=os.getenv('PROCESSING_MODE', 'simple'),
                batch_size=int(os.getenv('BATCH_SIZE', '32')),
                concurrency=int(os.getenv('CONCURRENCY', '8')),
                max_retries=int(os.getenv('MAX_RETRIES', '3')),
            ),
            redis=RedisConfig(
                url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
                cache_ttl=int(os.getenv('REDIS_CACHE_TTL', '2592000')),
                enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            ),
            minio=MinIOConfig(
                endpoint=os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
                access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin123'),
                bucket_name=os.getenv('MINIO_BUCKET_NAME', 'raw2md-documents'),
                secure=os.getenv('MINIO_SECURE', 'false').lower() == 'true',
            ),
            llm=LLMConfig(
                api_key=os.getenv('GOOGLE_API_KEY'),
                model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
                temperature=float(os.getenv('GEMINI_TEMPERATURE', '0.0')),
                max_tokens=int(os.getenv('GEMINI_MAX_TOKENS', '500')),
                timeout=int(os.getenv('GEMINI_TIMEOUT', '30')),
            ),
            ocr=OCRConfig(
                use_gpu=os.getenv('OCR_USE_GPU', 'true').lower() == 'true',
                lang=os.getenv('OCR_LANG', 'vie+eng'),
                confidence_threshold=float(os.getenv('OCR_CONFIDENCE_THRESHOLD', '0.5')),
                tesseract_path=os.getenv('TESSERACT_PATH', '/usr/bin/tesseract'),
                tesseract_config=os.getenv('TESSERACT_CONFIG', '--psm 6 --oem 3'),
                image_dpi=int(os.getenv('OCR_IMAGE_DPI', '300')),
                image_scale=float(os.getenv('OCR_IMAGE_SCALE', '2.0')),
                enable_preprocessing=os.getenv('OCR_ENABLE_PREPROCESSING', 'true').lower() == 'true',
                denoise_enabled=os.getenv('OCR_DENOISE_ENABLED', 'true').lower() == 'true',
                contrast_enhancement=os.getenv('OCR_CONTRAST_ENHANCEMENT', 'true').lower() == 'true',
                deskew_enabled=os.getenv('OCR_DESKEW_ENABLED', 'true').lower() == 'true',
            ),
            files=FileConfig(
                input_dir=os.getenv('INPUT_DIR', './input'),
                output_dir=os.getenv('OUTPUT_DIR', './output'),
                temp_dir=os.getenv('TEMP_DIR', './temp'),
                max_file_size_mb=int(os.getenv('MAX_FILE_SIZE_MB', '100')),
                supported_formats=[x.strip() for x in os.getenv('SUPPORTED_FORMATS', 'pdf,docx,html,txt,csv,xml,json,jpg,jpeg,png,tiff,bmp,webp').split(',')],
            ),
            logging=LoggingConfig(
                level=os.getenv('LOG_LEVEL', 'INFO'),
                format=os.getenv('LOG_FORMAT', 'json'),
                file=os.getenv('LOG_FILE'),
            ),
            performance=PerformanceConfig(
                async_io_workers=int(os.getenv('ASYNC_IO_WORKERS', '10')),
                ocr_batch_size=int(os.getenv('OCR_BATCH_SIZE', '8')),
                llm_batch_size=int(os.getenv('LLM_BATCH_SIZE', '5')),
                cache_enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
                metrics_enabled=os.getenv('METRICS_ENABLED', 'true').lower() == 'true',
            ),
            ray=RayConfig(
                address=os.getenv('RAY_ADDRESS', 'ray://localhost:10001'),
                num_cpus=int(os.getenv('RAY_NUM_CPUS', '8')),
                num_gpus=int(os.getenv('RAY_NUM_GPUS', '1')),
            ),
            monitoring=MonitoringConfig(
                prometheus_port=int(os.getenv('PROMETHEUS_PORT', '8000')),
                flower_port=int(os.getenv('FLOWER_PORT', '5555')),
                health_check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', '30')),
            ),
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'processing': {
                'mode': self.processing.mode,
                'batch_size': self.processing.batch_size,
                'concurrency': self.processing.concurrency,
                'max_retries': self.processing.max_retries,
            },
            'redis': {
                'url': self.redis.url,
                'cache_ttl': self.redis.cache_ttl,
                'enabled': self.redis.enabled,
            },
            'minio': {
                'endpoint': self.minio.endpoint,
                'access_key': self.minio.access_key,
                'secret_key': self.minio.secret_key,
                'bucket_name': self.minio.bucket_name,
                'secure': self.minio.secure,
            },
            'llm': {
                'api_key': self.llm.api_key,
                'model': self.llm.model,
                'temperature': self.llm.temperature,
                'max_tokens': self.llm.max_tokens,
                'timeout': self.llm.timeout,
            },
            'ocr': {
                'use_gpu': self.ocr.use_gpu,
                'lang': self.ocr.lang,
                'confidence_threshold': self.ocr.confidence_threshold,
                'tesseract_path': self.ocr.tesseract_path,
                'tesseract_config': self.ocr.tesseract_config,
                'image_dpi': self.ocr.image_dpi,
                'image_scale': self.ocr.image_scale,
                'enable_preprocessing': self.ocr.enable_preprocessing,
                'denoise_enabled': self.ocr.denoise_enabled,
                'contrast_enhancement': self.ocr.contrast_enhancement,
                'deskew_enabled': self.ocr.deskew_enabled,
            },
            'files': {
                'input_dir': self.files.input_dir,
                'output_dir': self.files.output_dir,
                'temp_dir': self.files.temp_dir,
                'max_file_size_mb': self.files.max_file_size_mb,
                'supported_formats': self.files.supported_formats,
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'file': self.logging.file,
            },
            'performance': {
                'async_io_workers': self.performance.async_io_workers,
                'ocr_batch_size': self.performance.ocr_batch_size,
                'llm_batch_size': self.performance.llm_batch_size,
                'cache_enabled': self.performance.cache_enabled,
                'metrics_enabled': self.performance.metrics_enabled,
            },
            'ray': {
                'address': self.ray.address,
                'num_cpus': self.ray.num_cpus,
                'num_gpus': self.ray.num_gpus,
            },
            'monitoring': {
                'prometheus_port': self.monitoring.prometheus_port,
                'flower_port': self.monitoring.flower_port,
                'health_check_interval': self.monitoring.health_check_interval,
            },
        }


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config.from_env()


def setup_logging(config: LoggingConfig):
    """Setup logging configuration."""
    import logging.handlers
    
    # Configure logging level
    level = getattr(logging, config.level)
    
    # Configure format
    if config.format == 'json':
        import json
        formatter = logging.Formatter(
            fmt='%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Configure handlers
    handlers = [logging.StreamHandler()]
    if config.file:
        handlers.append(logging.handlers.RotatingFileHandler(
            config.file, maxBytes=10*1024*1024, backupCount=5
        ))
    
    # Setup logging
    logging.basicConfig(
        level=level,
        format=formatter.format,
        handlers=handlers
    )
