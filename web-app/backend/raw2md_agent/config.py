"""
Configuration management for Raw2MD Agent.

Handles environment variables, default settings, and validation
for all processing modes (simple, batch, distributed).
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not available. Environment variables will not be loaded from .env file")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")


class ProcessingConfig(BaseModel):
    """Processing mode and performance settings."""
    
    mode: str = Field(default="simple", description="Processing mode: simple, batch, distributed")
    batch_size: int = Field(default=32, ge=1, le=100, description="Batch size for processing")
    concurrency: int = Field(default=8, ge=1, le=32, description="Number of concurrent workers")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")


class RedisConfig(BaseModel):
    """Redis configuration for caching and message broker."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    cache_ttl: int = Field(default=2592000, description="Cache TTL in seconds (30 days)")
    enabled: bool = Field(default=True, description="Enable Redis caching")


class MinIOConfig(BaseModel):
    """MinIO/S3 storage configuration."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    endpoint: str = Field(default="localhost:9000", description="MinIO endpoint")
    access_key: str = Field(default="minioadmin", description="Access key")
    secret_key: str = Field(default="minioadmin123", description="Secret key")
    bucket_name: str = Field(default="raw2md-documents", description="Bucket name")
    secure: bool = Field(default=False, description="Use HTTPS")


class LLMConfig(BaseModel):
    """Gemini 2.5 Flash LLM configuration."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    api_key: Optional[str] = Field(default=None, description="Google API key")
    model: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Temperature for generation")
    max_tokens: int = Field(default=500, ge=100, le=2000, description="Maximum output tokens")
    timeout: int = Field(default=30, ge=5, le=120, description="Request timeout in seconds")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        if v is None or v == "your_google_api_key_here":
            logging.warning("Google API key not configured. LLM mode will be disabled.")
        return v


class OCRConfig(BaseModel):
    """OCR engine configuration optimized for scanned PDFs."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    use_gpu: bool = Field(default=True, description="Enable GPU acceleration")
    lang: str = Field(default="vie+eng", description="OCR language code (vie+eng for Vietnamese + English)")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence threshold (lowered for scanned docs)")
    tesseract_path: str = Field(default="/usr/bin/tesseract", description="Tesseract binary path")
    
    # Tesseract-specific optimizations for scanned PDFs
    tesseract_config: str = Field(default="--psm 6 --oem 3", description="Tesseract configuration for scanned documents")
    image_dpi: int = Field(default=300, ge=150, le=600, description="DPI for image conversion (higher = better quality)")
    image_scale: float = Field(default=2.0, ge=1.0, le=4.0, description="Image scaling factor for OCR")
    
    # Preprocessing options
    enable_preprocessing: bool = Field(default=True, description="Enable image preprocessing before OCR")
    denoise_enabled: bool = Field(default=True, description="Enable denoising for scanned images")
    contrast_enhancement: bool = Field(default=True, description="Enable contrast enhancement")
    deskew_enabled: bool = Field(default=True, description="Enable automatic deskewing")


class FileConfig(BaseModel):
    """File processing configuration."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    input_dir: str = Field(default="./input", description="Input directory")
    output_dir: str = Field(default="./output", description="Output directory")
    temp_dir: str = Field(default="./temp", description="Temporary directory")
    max_file_size_mb: int = Field(default=100, ge=1, le=1000, description="Maximum file size in MB")
    supported_formats: List[str] = Field(
        default=["pdf", "docx", "html", "txt", "csv", "xml", "json", "jpg", "jpeg", "png", "tiff", "bmp", "webp"],
        description="Supported file formats"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format: json or text")
    file: Optional[str] = Field(default=None, description="Log file path")
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()


class PerformanceConfig(BaseModel):
    """Performance tuning configuration."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    async_io_workers: int = Field(default=10, ge=1, le=50, description="Async I/O workers")
    ocr_batch_size: int = Field(default=8, ge=1, le=32, description="OCR batch size")
    llm_batch_size: int = Field(default=5, ge=1, le=20, description="LLM batch size")
    cache_enabled: bool = Field(default=True, description="Enable caching")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")


class RayConfig(BaseModel):
    """Ray distributed processing configuration."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    address: str = Field(default="ray://localhost:10001", description="Ray cluster address")
    num_cpus: int = Field(default=8, ge=1, le=64, description="Number of CPUs")
    num_gpus: int = Field(default=1, ge=0, le=8, description="Number of GPUs")


class MonitoringConfig(BaseModel):
    """Monitoring and health check configuration."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    prometheus_port: int = Field(default=8000, ge=1000, le=65535, description="Prometheus metrics port")
    flower_port: int = Field(default=5555, ge=1000, le=65535, description="Flower monitoring port")
    health_check_interval: int = Field(default=30, ge=5, le=300, description="Health check interval in seconds")


class Config(BaseModel):
    """Main configuration class combining all settings."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    minio: MinIOConfig = Field(default_factory=MinIOConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    files: FileConfig = Field(default_factory=FileConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    ray: RayConfig = Field(default_factory=RayConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
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
                supported_formats=os.getenv('SUPPORTED_FORMATS', 
                    'pdf,docx,html,txt,csv,xml,json,jpg,jpeg,png,tiff,bmp,webp'
                ).split(','),
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
    
    def setup_logging(self) -> None:
        """Configure logging based on settings."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        if self.logging.format.lower() == 'json':
            import json
            
            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    log_entry = {
                        'timestamp': self.formatTime(record),
                        'logger': record.name,
                        'level': record.levelname,
                        'message': record.getMessage(),
                    }
                    if record.exc_info:
                        log_entry['exception'] = self.formatException(record.exc_info)
                    return json.dumps(log_entry)
            
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(log_format)
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, self.logging.level),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                *([logging.FileHandler(self.logging.file)] if self.logging.file else []),
            ]
        )
        
        # Set formatter for all handlers
        for handler in logging.getLogger().handlers:
            handler.setFormatter(formatter)
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.files.input_dir,
            self.files.output_dir,
            self.files.temp_dir,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
        _config.setup_logging()
        _config.ensure_directories()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
    _config.setup_logging()
    _config.ensure_directories()
