#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vietnamese Legal Metadata Extractor - Flask Application
Main entry point for the API server.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from werkzeug.middleware.proxy_fix import ProxyFix

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import modules
from src.utils import config, DatabaseManager, register_routes

# Import Flask
try:
    from flask import Flask, request, make_response
except ImportError as e:
    print(f"[ERROR] Flask import error: {e}")
    print("Please run: pip install flask flask-cors werkzeug")
    sys.exit(1)

def create_app():
    """Create and configure Flask application"""
    # Setup logging
    logger = config.setup_logging()
    
    # Ensure directories exist
    config.ensure_directories()
    
    # Create Flask app
    app = Flask(__name__)
    app.config.update({
        'SECRET_KEY': config.SECRET_KEY,
        'MAX_CONTENT_LENGTH': int(config.MAX_FILE_SIZE_MB) * 1024 * 1024,
    })
    
    # Enable ProxyFix for reverse proxy deployment
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
    # CORS configuration
    ALLOWED_ORIGINS = {
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5500',
        'http://127.0.0.1:5500',
    }
    
    @app.after_request
    def after_request(response):
        """Add CORS headers"""
        origin = request.headers.get('Origin')
        if origin in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
        return response
    
    # Handle preflight OPTIONS requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get('Origin')
            resp = make_response('', 204)
            if origin in ALLOWED_ORIGINS:
                resp.headers['Access-Control-Allow-Origin'] = origin
                resp.headers['Access-Control-Allow-Credentials'] = 'true'
                resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
                resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
            return resp
    
    # Initialize database
    db_manager = DatabaseManager(str(config.DATABASE_PATH))
    
    # Register routes
    register_routes(app, db_manager)
    
    logger.info("Vietnamese Legal Metadata Extractor Flask application created successfully")
    return app, db_manager

def print_startup_info():
    """Print startup information"""
    print("Vietnamese Legal Metadata Extractor")
    print("=" * 50)
    print(f"API Server: http://localhost:{config.API_PORT}")
    print(f"Database: {config.DATABASE_PATH}")
    print(f"Upload folder: {config.UPLOAD_FOLDER}")
    print(f"OCR: {'Enabled' if config.OCR_ENABLED else 'Disabled'}")
    print("=" * 50)

def main():
    """Main application entry point"""
    print_startup_info()
    
    # Disable Flask's automatic .env loading to avoid encoding issues
    os.environ['FLASK_SKIP_DOTENV'] = '1'
    
    # Create application
    app, _ = create_app()
    
    # Run application
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.DEBUG,
        threaded=True
    )

if __name__ == '__main__':
    main()
