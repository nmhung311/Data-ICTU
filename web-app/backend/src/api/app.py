#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raw2MD Agent Flask Backend API - Optimized
Clean, modular architecture with performance improvements
"""
# pylint: disable=unused-variable,unused-argument

import os
import sys
from pathlib import Path
from typing import Tuple, Optional, Any
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

# Fix annotationlib import error for Python 3.11+
def fix_annotationlib_import():
    """Fix annotationlib import issues for Python 3.11+"""
    try:
        import annotationlib
        # Check if the problematic function exists
        if hasattr(annotationlib, 'get_annotate_from_class_namespace'):
            return True
        else:
            # Only patch if we detect the specific missing function
            def dummy_get_annotate_from_class_namespace(obj):
                return getattr(obj, '__annotations__', {})
            annotationlib.get_annotate_from_class_namespace = dummy_get_annotate_from_class_namespace
            print("WARNING: Applied annotationlib monkey patch - consider pinning pydantic version")
            return True
    except ImportError:
        # annotationlib not available, which is fine
        return True
    except Exception as e:
        print(f"WARNING: annotationlib error: {e} - consider pinning pydantic version")
        return False

# Apply the fix immediately
fix_annotationlib_import()

# Add project root to Python path (moved from config.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import modules from new structure
from src.utils import config, DatabaseManager, register_routes

# Import Flask with optimized error handling
try:
    from flask_imports import Flask, FLASK_AVAILABLE, request, make_response  # CORS not used directly
    if not FLASK_AVAILABLE:
        raise ImportError("Flask not available")
except ImportError as e:
    print(f"[ERROR] Flask import error: {e}")
    print("Please run: pip install flask flask-cors werkzeug")
    sys.exit(1)

# Global app instance for caching
_app_instance: Optional[Tuple[Any, Any]] = None

def create_app() -> Tuple[Any, Any]:
    """Create and configure Flask application with caching"""
    global _app_instance
    
    # Return cached instance if available
    if _app_instance is not None:
        return _app_instance
    
    # Setup logging
    logger = config.setup_logging()
    
    # Ensure directories exist
    config.ensure_directories()
    
    # Create Flask app with optimized settings
    app = Flask(__name__)
    app.config.update({
        'SECRET_KEY': config.SECRET_KEY,
        'MAX_CONTENT_LENGTH': int(config.MAX_FILE_SIZE_MB) * 1024 * 1024,
        'SEND_FILE_MAX_AGE_DEFAULT': 0,  # Disable caching
        'PERMANENT_SESSION_LIFETIME': timedelta(seconds=0),  # Disable session caching
        # 'JSONIFY_PRETTYPRINT_REGULAR': False,  # Deprecated in Flask 2.3+, removed
    })
    
    # Enable ProxyFix for reverse proxy deployment
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
    # CORS configuration with proper headers
    ALLOWED_ORIGINS = {
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5500',
        'http://127.0.0.1:5500',
    }
    
    def _origin_allowed(origin: Optional[str]) -> bool:
        return origin in ALLOWED_ORIGINS
    
    @app.after_request
    def _after_request(response):  # pyright: ignore[reportUnusedFunction]
        """Add CORS headers and disable caching"""
        origin = request.headers.get('Origin')
        # Always set Vary for proper caching
        response.headers['Vary'] = 'Origin'
        
        if _origin_allowed(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = (
                'Content-Type,Authorization,X-Requested-With,Accept,Cache-Control,Pragma'
            )
        
        # Disable caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    # Handle preflight OPTIONS requests
    @app.before_request
    def _handle_preflight():  # pyright: ignore[reportUnusedFunction]
        """Handle CORS preflight requests"""
        if request.method == "OPTIONS":
            origin = request.headers.get('Origin')
            resp = make_response('', 204)
            resp.headers['Vary'] = 'Origin'
            if _origin_allowed(origin):
                resp.headers['Access-Control-Allow-Origin'] = origin
                resp.headers['Access-Control-Allow-Credentials'] = 'true'
                resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
                resp.headers['Access-Control-Allow-Headers'] = (
                    'Content-Type,Authorization,X-Requested-With,Accept,Cache-Control,Pragma'
                )
                resp.headers['Access-Control-Max-Age'] = '3600'
            return resp
    
    # Initialize database
    db_manager = DatabaseManager(str(config.DATABASE_PATH))
    
    # Register routes
    register_routes(app, db_manager)
    
    # Cache the instance
    _app_instance = (app, db_manager)
    
    logger.info("Raw2MD Agent Flask application created successfully")
    return app, db_manager

def print_startup_info() -> None:
    """Print startup information in a clean format"""
    print("Raw2MD Agent Flask Backend API - Optimized Version")
    print("=" * 60)
    
    # Configuration info
    config_info = [
        ("Project root", str(config.PROJECT_ROOT)),
        ("Database", str(config.DATABASE_PATH)),
        ("Upload folder", str(config.UPLOAD_FOLDER)),
        ("Output folder", str(config.OUTPUT_FOLDER)),
        ("Raw2MD Agent", "Enabled" if config.RAW2MD_AGENT_ENABLED else "Disabled"),
        ("OCR", "Enabled" if config.OCR_ENABLED else "Disabled"),
        ("Metadata extraction", "Enabled" if config.METADATA_EXTRACTION_ENABLED else "Disabled"),
    ]
    
    for label, value in config_info:
        print(f"{label:20}: {value}")
    
    # API endpoints
    endpoints = [
        ("GET", "/api/health", "Health check with stats"),
        ("GET", "/api/supported-formats", "Supported file formats"),
        ("POST", "/api/process", "Process document"),
        ("GET", "/api/result/<id>", "Get result"),
        ("GET", "/api/download/<id>", "Download markdown"),
        ("GET", "/api/files", "List uploaded files"),
        ("GET", "/api/results", "List processing results"),
        ("GET", "/api/stats", "Get system statistics"),
        ("GET", "/api/ocr-status", "OCR status"),
        ("GET", "/api/config", "Get system configuration"),
        ("GET", "/api/installation-guide", "Installation guide"),
    ]
    
    print(f"\nAPI endpoints:")
    for method, endpoint, description in endpoints:
        print(f"  {method:4} {endpoint:25} - {description}")
    
    print(f"\nAccess the API at: http://localhost:{config.API_PORT}")
    print("=" * 60)

def main() -> None:
    """Main application entry point with optimized startup"""
    print_startup_info()
    
    # Create application
    app, _ = create_app()
    
    # Disable Flask's automatic .env loading
    os.environ['FLASK_SKIP_DOTENV'] = '1'
    
    # Run application with optimized settings
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.DEBUG,
        threaded=True,  # Enable threading for better performance
        use_reloader=False if not config.DEBUG else True  # Disable reloader in production
    )

if __name__ == '__main__':
    main()