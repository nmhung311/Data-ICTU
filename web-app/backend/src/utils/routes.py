#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routes module for Raw2MD Agent Backend
API endpoints and route handlers
"""

import os
import logging
import uuid
from typing import Union
from pathlib import Path
from io import BytesIO
from flask import Flask, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from .config import config
from .database import DatabaseManager
from .utils import (
    validate_file_upload, process_document_advanced, 
    process_document_simple, detect_file_type
)
from ..api.metadata_routes import register_metadata_routes

logger = logging.getLogger(__name__)

def _detect_tesseract() -> bool:
    """Detect if tesseract is available"""
    import shutil
    return bool(shutil.which('tesseract') or config.TESSERACT_PATH)

def _detect_paddleocr() -> bool:
    """Detect if paddleocr is available"""
    try:
        import paddleocr  # type: ignore
        return True
    except Exception:
        return False

def _detect_enhanced_splitter() -> bool:
    """Detect if enhanced splitter is available"""
    try:
        from .utils import process_document_advanced
        return callable(process_document_advanced)
    except Exception:
        return False

def _to_bool(value, default=False):
    """Convert value to boolean"""
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 't', 'yes', 'y', 'on'}

def _get_paging():
    """Get pagination parameters with validation"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        return 50, 0, jsonify({'error': 'limit/offset must be integers'}), 400
    limit = min(max(limit, 1), 1000)
    offset = max(offset, 0)
    return limit, offset, None, None

def register_routes(app: Flask, db_manager: DatabaseManager) -> None:
    """Register all API routes
    
    This function registers all Flask routes for the Raw2MD Agent API.
    All functions defined within are automatically registered as route handlers
    by Flask decorators, so linter warnings about "not accessed" are false positives.
    
    Note: All functions below are accessed by Flask's routing system via decorators.
    """
    # Error handler for file too large
    @app.errorhandler(RequestEntityTooLarge)
    def handle_413(e):  # type: ignore
        return jsonify({'error': 'File too large', 'max_size_mb': config.MAX_FILE_SIZE_MB}), 413
    
    # All functions below are Flask route handlers and are accessed via decorators
    # This suppresses linter warnings about unused functions
    
    @app.route('/api/health', methods=['GET'])
    def health() -> Union[Response, tuple]:
        """Health check endpoint with system information"""
        try:
            stats = db_manager.get_stats()
            return jsonify({
                'status': 'healthy',
                'database': 'SQLite',
                'enhanced_splitter_available': _detect_enhanced_splitter(),
                'stats': stats,
                'config': {
                    'ocr_enabled': config.OCR_ENABLED,
                    'tesseract_available': _detect_tesseract(),
                    'paddleocr_available': _detect_paddleocr(),
                    'metadata_extraction_enabled': config.METADATA_EXTRACTION_ENABLED,
                    'max_file_size_mb': config.MAX_FILE_SIZE_MB,
                    'allowed_extensions': sorted(list(config.ALLOWED_EXTENSIONS))
                }
            })
        except Exception as e:
            logger.exception("Health check failed")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    @app.route('/api/supported-formats', methods=['GET'])
    def supported_formats() -> Response:
        """Get supported file formats"""
        return jsonify({
            'formats': list(config.ALLOWED_EXTENSIONS),
            'max_size_mb': config.MAX_FILE_SIZE_MB
        })
    
    @app.route('/api/process', methods=['POST'])
    def process_file() -> Union[Response, tuple]:
        """Process uploaded file"""
        try:
            # Check if file is present
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file provided'}), 400
            
            file = request.files['file']
            
            # Validate file
            validation = validate_file_upload(file, config.MAX_FILE_SIZE_MB, config.ALLOWED_EXTENSIONS)
            if not validation['valid']:
                return jsonify({'success': False, 'error': validation['error']}), 400
            
            # Parse options from form or JSON
            payload = request.form if request.form else (request.get_json(silent=True) or {})
            ocr_enabled = _to_bool(payload.get('ocr_enabled'), True)
            extract_metadata = _to_bool(payload.get('extract_metadata'), False)
            extract_images = _to_bool(payload.get('extract_images'), False)
            
            # Save file permanently
            original_name = file.filename or 'unknown'
            safe_name = secure_filename(original_name) or 'file'
            file_type = detect_file_type(safe_name)
            
            # Generate unique filename
            dest_name = f"{uuid.uuid4().hex}.{file_type}"
            dest_path = Path(config.UPLOAD_FOLDER) / dest_name
            file.save(str(dest_path))
            
            try:
                # Process document
                logger.info(f"Processing file: {original_name} -> {dest_name}, type: {file_type}")
                
                options = {
                    'ocr_enabled': ocr_enabled,
                    'extract_metadata': extract_metadata,
                    'extract_images': extract_images
                }
                
                if extract_metadata and config.RAW2MD_AGENT_ENABLED:
                    logger.info("Using advanced processing")
                    result = process_document_advanced(str(dest_path), options)
                else:
                    logger.info("Using simple processing")
                    result = process_document_simple(str(dest_path), options)
                
                logger.info(f"Processing result: {result.get('success', False)}")
                
                if not result.get('success'):
                    logger.error(f"Processing failed: {result.get('error', 'Unknown error')}")
                    return jsonify({
                        'success': False,
                        'error': result.get('error', 'Processing failed')
                    }), 500
                
                # Add file information
                result.update({
                    'filename': original_name,
                    'stored_filename': dest_name,
                    'file_size': validation['file_size'],
                    'file_type': file_type
                })
                
                # Save to database
                result_id = db_manager.save_result(result)
                result['result_id'] = result_id
                
                # Save file info
                db_manager.save_file({
                    'filename': original_name,
                    'stored_filename': dest_name,
                    'file_type': file_type,
                    'file_size': validation['file_size'],
                    'file_path': str(dest_path)
                })
                
                logger.info(f"File processed successfully: {original_name}")
                return jsonify(result)
                
            except Exception as e:
                # Clean up file if processing failed
                try:
                    os.unlink(dest_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to delete file after processing error: {cleanup_error}")
                raise
        
        except Exception as e:
            logger.exception("File processing failed")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/result/<result_id>', methods=['GET'])
    def get_result(result_id: str) -> Union[Response, tuple]:
        """Get processing result by ID"""
        try:
            result = db_manager.get_result(result_id)
            if not result:
                return jsonify({'error': 'Result not found'}), 404
            
            return jsonify(result)
        except Exception as e:
            logger.exception(f"Failed to get result {result_id}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/download/<result_id>', methods=['GET'])
    def download_result(result_id: str) -> Union[Response, tuple]:
        """Download markdown file"""
        try:
            result = db_manager.get_result(result_id)
            if not result:
                return jsonify({'error': 'Result not found'}), 404
            
            content = result.get('markdown_content')
            if not content:
                return jsonify({'error': 'No markdown content available'}), 404
            
            # Use memory buffer instead of temp file
            buf = BytesIO(content.encode('utf-8'))
            
            # Sanitize download name
            base = secure_filename((result.get('filename') or 'document').rsplit('.', 1)[0]) or 'document'
            download_name = f"{base}.md"
            
            return send_file(
                buf,
                as_attachment=True,
                download_name=download_name,
                mimetype='text/markdown'
            )
        except Exception as e:
            logger.exception(f"Failed to download result {result_id}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/files', methods=['GET'])
    def list_files() -> Union[Response, tuple]:
        """List uploaded files"""
        try:
            limit, offset, err_resp, code = _get_paging()
            if err_resp:
                return err_resp, code
            
            files = db_manager.list_files(limit, offset)
            return jsonify({'files': files, 'limit': limit, 'offset': offset})
        except Exception as e:
            logger.exception("Failed to list files")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/results', methods=['GET'])
    def list_results() -> Union[Response, tuple]:
        """List processing results"""
        try:
            limit, offset, err_resp, code = _get_paging()
            if err_resp:
                return err_resp, code
            
            results = db_manager.list_results(limit, offset)
            return jsonify({'results': results, 'limit': limit, 'offset': offset})
        except Exception as e:
            logger.exception("Failed to list results")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/stats', methods=['GET'])
    def get_stats() -> Union[Response, tuple]:
        """Get system statistics"""
        try:
            stats = db_manager.get_stats()
            return jsonify(stats)
        except Exception as e:
            logger.exception("Failed to get stats")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ocr-status', methods=['GET'])
    def ocr_status() -> Union[Response, tuple]:
        """Get OCR status and configuration"""
        try:
            return jsonify({
                'ocr_enabled': config.OCR_ENABLED,
                'tesseract_available': _detect_tesseract(),
                'paddleocr_available': _detect_paddleocr()
            })
        except Exception as e:
            logger.exception("Failed to get OCR status")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/config', methods=['GET'])
    def get_config() -> Union[Response, tuple]:
        """Get system configuration"""
        try:
            return jsonify(config.get_config_dict())
        except Exception as e:
            logger.exception("Failed to get config")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/sources', methods=['POST'])
    def upload_source() -> Union[Response, tuple]:
        """Upload a source file"""
        try:
            # Check if file is present
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file provided'}), 400
            
            file = request.files['file']
            
            # Validate file
            validation = validate_file_upload(file, config.MAX_FILE_SIZE_MB, config.ALLOWED_EXTENSIONS)
            if not validation['valid']:
                return jsonify({'success': False, 'error': validation['error']}), 400
            
            # Save file permanently
            original_name = file.filename or 'unknown'
            safe_name = secure_filename(original_name) or 'file'
            file_type = detect_file_type(safe_name)
            
            # Generate unique filename
            dest_name = f"{uuid.uuid4().hex}.{file_type}"
            dest_path = Path(config.UPLOAD_FOLDER) / dest_name
            file.save(str(dest_path))
            
            # Save file info to database
            file_id = db_manager.save_file({
                'filename': original_name,
                'stored_filename': dest_name,
                'file_type': file_type,
                'file_size': validation['file_size'],
                'file_path': str(dest_path)
            })
            
            logger.info(f"Source uploaded successfully: {original_name} -> {dest_name}")
            return jsonify({
                'success': True,
                'source_id': file_id,
                'filename': original_name,
                'file_type': file_type,
                'file_size': validation['file_size']
            })
            
        except Exception as e:
            logger.exception("Source upload failed")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/sources/<source_id>', methods=['DELETE'])
    def delete_source(source_id: str) -> Union[Response, tuple]:
        """Delete a source file"""
        try:
            # Get file info from database
            file_info = db_manager.get_file(source_id)
            if not file_info:
                return jsonify({'success': False, 'error': 'Source not found'}), 404
            
            # Delete physical file
            file_path = Path(file_info['file_path'])
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_path}: {e}")
            
            # Delete from database
            db_manager.delete_file(source_id)
            
            logger.info(f"Source deleted successfully: {file_info['filename']}")
            return jsonify({'success': True, 'message': 'Source deleted successfully'})
            
        except Exception as e:
            logger.exception(f"Failed to delete source {source_id}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/sources/<source_id>', methods=['PUT'])
    def rename_source(source_id: str) -> Union[Response, tuple]:
        """Rename a source file"""
        try:
            data = request.get_json()
            if not data or 'name' not in data:
                return jsonify({'success': False, 'error': 'New name not provided'}), 400
            
            new_name = data['name'].strip()
            if not new_name:
                return jsonify({'success': False, 'error': 'New name cannot be empty'}), 400
            
            # Get file info from database
            file_info = db_manager.get_file(source_id)
            if not file_info:
                return jsonify({'success': False, 'error': 'Source not found'}), 404
            
            # Update filename in database
            db_manager.update_file(source_id, {'filename': new_name})
            
            logger.info(f"Source renamed successfully: {file_info['filename']} -> {new_name}")
            return jsonify({'success': True, 'message': 'Source renamed successfully'})
            
        except Exception as e:
            logger.exception(f"Failed to rename source {source_id}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/sources', methods=['GET'])
    def list_sources() -> Union[Response, tuple]:
        """List all source files"""
        try:
            limit, offset, err_resp, code = _get_paging()
            if err_resp:
                return err_resp, code
            
            files = db_manager.list_files(limit, offset)
            return jsonify({'sources': files, 'limit': limit, 'offset': offset})
        except Exception as e:
            logger.exception("Failed to list sources")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/sources/<source_id>/info', methods=['GET'])
    def get_source_info(source_id: str) -> Union[Response, tuple]:
        """Get source file info for display"""
        try:
            # Get file info from database
            file_info = db_manager.get_file(source_id)
            if not file_info:
                return jsonify({'success': False, 'error': 'Source not found'}), 404
            
            file_path = Path(file_info['file_path'])
            if not file_path.exists():
                return jsonify({'success': False, 'error': 'File not found on disk'}), 404
            
            file_type = file_info['file_type'].lower()
            
            if file_type == 'pdf':
                return jsonify({
                    'success': True,
                    'content_type': 'pdf',
                    'filename': file_info['filename']
                })
            elif file_type in ['md', 'markdown', 'txt']:
                # For text files, read and return content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return jsonify({
                        'success': True,
                        'content_type': 'text',
                        'content': content,
                        'filename': file_info['filename']
                    })
                except UnicodeDecodeError:
                    # Try with different encoding
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    return jsonify({
                        'success': True,
                        'content_type': 'text',
                        'content': content,
                        'filename': file_info['filename']
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported file type: {file_type}'
                }), 400
                
        except Exception as e:
            logger.exception(f"Failed to get source info {source_id}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/sources/<source_id>/content', methods=['GET'])
    def get_source_content(source_id: str) -> Union[Response, tuple]:
        """Serve source file content directly"""
        try:
            # Get file info from database
            file_info = db_manager.get_file(source_id)
            if not file_info:
                return jsonify({'success': False, 'error': 'Source not found'}), 404
            
            file_path = Path(file_info['file_path'])
            if not file_path.exists():
                return jsonify({'success': False, 'error': 'File not found on disk'}), 404
            
            file_type = file_info['file_type'].lower()
            
            if file_type == 'pdf':
                # For PDF, serve file directly for iframe
                return send_file(
                    str(file_path),
                    as_attachment=False,
                    mimetype='application/pdf'
                )
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported file type: {file_type}'
                }), 400
                
        except Exception as e:
            logger.exception(f"Failed to get source content {source_id}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/installation-guide', methods=['GET'])
    def installation_guide() -> Response:
        """Get installation guide"""
        return jsonify({
            'title': 'Raw2MD Agent Installation Guide',
            'steps': [
                '1. Install Python 3.11+',
                '2. Install dependencies: pip install -r requirements.txt',
                '3. Configure environment variables',
                '4. Run: python app.py',
                '5. Access API at: http://localhost:5000'
            ],
            'requirements': [
                'Python 3.11+',
                'Flask 3.0+',
                'PyMuPDF',
                'python-docx',
                'PaddleOCR (optional)',
                'Tesseract (optional)'
            ]
        })
    
    # Register metadata routes
    register_metadata_routes(app, db_manager)
    
    # Suppress linter warnings about unused functions
    # These functions are accessed by Flask's routing system via decorators
    _ = (health, supported_formats, process_file, get_result, download_result, 
         list_files, list_results, get_stats, ocr_status, get_config, installation_guide,
         upload_source, delete_source, rename_source, list_sources, get_source_info, get_source_content)
