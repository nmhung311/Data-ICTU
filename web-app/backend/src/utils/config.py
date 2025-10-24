#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module for Raw2MD Agent Backend
Centralized configuration management
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Dict, Any
from logging.handlers import RotatingFileHandler

def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

class Config:
    """Main configuration class"""

    # Project Configuration
    PROJECT_ROOT = Path(__file__).resolve().parents[3]  # Updated for new structure: src/utils -> backend -> web-app -> root
    # Đừng chỉnh sys.path ở đây. Nếu thực sự cần, làm ở entrypoint.
    # sys.path.insert(0, str(PROJECT_ROOT))

    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'raw2md-agent-secret-key-2024')
    DEBUG = _env_bool('FLASK_DEBUG', False)  # FLASK_ENV đã deprecated

    # Database Configuration
    DATA_DIR = PROJECT_ROOT / 'data'
    DATABASE_PATH = DATA_DIR / 'raw2md_agent.db'

    # File Upload Configuration
    UPLOAD_FOLDER = DATA_DIR / 'uploads'
    OUTPUT_FOLDER = DATA_DIR / 'outputs'  # Updated to new structure
    MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '100'))
    ALLOWED_EXTENSIONS = {
        'pdf', 'docx', 'html', 'htm', 'txt', 'csv', 'xml', 'json',
        'jpg', 'jpeg', 'png', 'tiff', 'bmp', 'webp', 'md', 'markdown'
    }

    # Processing Configuration
    OCR_ENABLED = _env_bool('OCR_ENABLED', True)
    METADATA_EXTRACTION_ENABLED = _env_bool('METADATA_EXTRACTION_ENABLED', True)

    # OCR Configuration
    TESSERACT_PATH = os.environ.get('TESSERACT_PATH', '')  # để trống và auto-detect
    OCR_LANG = os.environ.get('OCR_LANG', 'vie+eng')
    OCR_CONFIDENCE_THRESHOLD = float(os.environ.get('OCR_CONFIDENCE_THRESHOLD', '0.5'))
    TESSERACT_CONFIG = os.environ.get('TESSERACT_CONFIG', '--psm 6 --oem 3')

    # API Configuration
    API_HOST = os.environ.get('API_HOST', '0.0.0.0')
    API_PORT = int(os.environ.get('API_PORT', '5000'))

    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING').upper()
    LOG_DIR = PROJECT_ROOT / 'logs'
    LOG_FILE = LOG_DIR / 'raw2md_api.log'
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'

    # Raw2MD Agent Configuration - Tắt để sử dụng EnhancedVnLegalSplitter
    RAW2MD_AGENT_ENABLED = _env_bool('RAW2MD_AGENT_ENABLED', False)

    @classmethod
    def setup_logging(cls):
        """Setup logging configuration with rotation"""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

        root = logging.getLogger()
        # Xóa handler cũ (nếu có) để basicConfig/handlers mới có tác dụng
        for h in list(root.handlers):
            root.removeHandler(h)

        file_handler = RotatingFileHandler(
            cls.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
        )
        stream_handler = logging.StreamHandler()

        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL, logging.WARNING),
            format=cls.LOG_FORMAT,
            handlers=[file_handler, stream_handler]
        )

        # Giảm ồn
        quiet_libraries = [
            'werkzeug', 'urllib3', 'requests', 'PIL', 'PIL.Image',
            'PIL.PngImagePlugin', 'PIL.JpegImagePlugin', 'matplotlib',
            'matplotlib.font_manager', 'paddleocr', 'paddlepaddle'
        ]
        for lib in quiet_libraries:
            logging.getLogger(lib).setLevel(logging.WARNING)

        # Cảnh báo nếu SECRET_KEY dùng default
        if cls.SECRET_KEY == 'raw2md-agent-secret-key-2024':
            logging.getLogger(__name__).warning(
                "Using default SECRET_KEY. Set SECRET_KEY in environment for production."
            )

        # Auto-detect tesseract nếu không khai báo
        if not cls.TESSERACT_PATH:
            found = shutil.which('tesseract')
            if found:
                cls.TESSERACT_PATH = found
                logging.getLogger(__name__).info(f"Detected tesseract at {cls.TESSERACT_PATH}")
            elif cls.OCR_ENABLED:
                logging.getLogger(__name__).warning(
                    "OCR_ENABLED=True but TESSERACT_PATH not found. OCR will likely fail."
                )

        return logging.getLogger(__name__)

    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get configuration as dictionary (an toàn để expose ra API)"""
        safe = {
            'database_path': str(cls.DATABASE_PATH),
            'upload_folder': str(cls.UPLOAD_FOLDER),
            'output_folder': str(cls.OUTPUT_FOLDER),
            'max_file_size_mb': cls.MAX_FILE_SIZE_MB,
            'allowed_extensions': sorted(list(cls.ALLOWED_EXTENSIONS)),
            'ocr_enabled': cls.OCR_ENABLED,
            'metadata_extraction_enabled': cls.METADATA_EXTRACTION_ENABLED,
            'raw2md_agent_enabled': cls.RAW2MD_AGENT_ENABLED,
            'debug': cls.DEBUG,
            'ocr_lang': cls.OCR_LANG,
            'ocr_confidence_threshold': cls.OCR_CONFIDENCE_THRESHOLD,
            'tesseract_config': cls.TESSERACT_CONFIG
        }
        # Không expose SECRET_KEY, TESSERACT_PATH
        return safe

    @classmethod
    def allowed_file(cls, filename: str) -> bool:
        """Case-insensitive extension check"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS

# Global config instance
config = Config()
