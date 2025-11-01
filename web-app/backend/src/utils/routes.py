#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routes module for Raw2MD Agent Backend
API endpoints and route handlers
"""

import os
import logging
import uuid
import mimetypes
import markdown
import datetime
from typing import Union
from pathlib import Path
from io import BytesIO
from flask import Flask, request, jsonify, send_file, Response, abort
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

# Thư mục gốc an toàn chứa file nguồn
SAFE_BASE_DIR = Path(getattr(config, "UPLOAD_FOLDER", "uploads")).resolve()

def normalize_file_path(raw_path: str) -> Path:
    """
    Normalize file path from database to work in Docker container.
    Handles Windows paths that need to be converted to container paths.
    """
    raw_path_str = str(raw_path)
    
    # Convert Windows path to container path if needed
    if '\\' in raw_path_str:
        # Windows path detected, extract filename using string split
        # Handle both pure Windows paths and mixed paths
        # Split by backslash and take the last part (filename)
        parts = raw_path_str.replace('/', '\\').split('\\')
        filename = parts[-1] if parts else raw_path_str.split('/')[-1]
        
        # If filename is empty or same as original, try alternative method
        if not filename or filename == raw_path_str:
            # Try to extract from the end after last separator
            import re
            # Match filename with extension at the end
            match = re.search(r'([^\\/]+\.\w+)$', raw_path_str)
            if match:
                filename = match.group(1)
            else:
                # Last resort: use whole string as filename
                filename = raw_path_str
        
        file_path = config.UPLOAD_FOLDER / filename
        logger.info(f"Converted Windows path {raw_path} to container path {file_path}")
    else:
        file_path = Path(raw_path)
    
    # Resolve path
    try:
        file_path = file_path.resolve()
    except (OSError, RuntimeError):
        # If resolve fails (e.g., Windows path in Linux), try relative to UPLOAD_FOLDER
        if not file_path.is_absolute():
            file_path = config.UPLOAD_FOLDER / file_path
        else:
            # Try extracting just the filename again
            raw_path_str = str(raw_path)
            if '\\' in raw_path_str:
                parts = raw_path_str.replace('/', '\\').split('\\')
                filename = parts[-1] if parts else raw_path_str.split('/')[-1]
            else:
                filename = Path(raw_path).name
            file_path = config.UPLOAD_FOLDER / filename
    
    return file_path
# Calculate frontend directory - use absolute path from __file__
# __file__ = .../web-app/backend/src/utils/routes.py
# frontend = .../web-app/frontend
FRONTEND_DIR = (Path(__file__).parent.parent.parent.parent / "frontend").resolve()
logger.info(f"FRONTEND_DIR resolved to: {FRONTEND_DIR}, exists: {FRONTEND_DIR.exists()}")

MIME_MAP = {
    "pdf": "application/pdf",
    "txt": "text/plain; charset=utf-8",
    "md":  "text/markdown; charset=utf-8",
    "markdown": "text/markdown; charset=utf-8",
    "html": "text/html; charset=utf-8",
    "xml": "application/xml; charset=utf-8",
    "json": "application/json; charset=utf-8",
}

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
            
            # Get original extension
            original_ext = Path(original_name).suffix.lower() if original_name else '.unknown'
            if not original_ext or original_ext == '.':
                original_ext = '.unknown'
            
            # Generate unique filename with original extension
            dest_name = f"{uuid.uuid4().hex}{original_ext}"
            dest_path = Path(config.UPLOAD_FOLDER) / dest_name
            file.save(str(dest_path))
            
            # Save file info to database
            file_id = db_manager.save_source({
                'filename': original_name,
                'stored_filename': dest_name,
                'file_type': file_type,
                'file_size': validation['file_size'],
                'file_path': str(dest_path)
            })
            
            # Auto-process metadata if enabled
            if config.METADATA_EXTRACTION_ENABLED:
                try:
                    logger.info(f"Auto-processing metadata for source: {file_id}")

                    file_info = db_manager.get_source(file_id)
                    if file_info:
                        file_path = normalize_file_path(file_info['file_path'])
                        if file_path.exists():
                            from .utils import process_document_simple
                            from src.core.document_splitter import EnhancedVnLegalSplitter
                            from src.core.category_classifier import classify_by_filename

                            result = process_document_simple(
                                str(file_path),
                                options={'ocr_enabled': config.OCR_ENABLED}
                            )
                            if result and result.get('success'):
                                text_for_split = result.get('cleaned_text') or result.get('raw_text') or ''
                                if text_for_split:
                                    splitter = EnhancedVnLegalSplitter(use_llm=True)  # Enable LLM for title generation
                                    filename = file_info.get('filename', '')
                                    blocks = splitter.split_document(text_for_split, filename)

                                    if blocks:
                                        with db_manager.get_connection() as conn:
                                            cursor = conn.cursor()
                                            saved_blocks = 0
                                            for block in blocks:
                                                try:
                                                    final_category = classify_by_filename(filename)
                                                    cursor.execute("""
                                                        INSERT INTO metadata_blocks 
                                                        (id, doc_id, department, type_data, category, content, source, date, created_at)
                                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                                                    """, (
                                                        str(uuid.uuid4()),
                                                        file_id,
                                                        getattr(block, 'department', 'Training Department'),
                                                        getattr(block, 'type_data', 'markdown'),
                                                        final_category,
                                                        getattr(block, 'content', ''),
                                                        getattr(block, 'source', filename),
                                                        getattr(block, 'date', '')
                                                    ))
                                                    saved_blocks += 1
                                                except Exception as block_error:
                                                    logger.warning(f"Failed to save block: {block_error}")
                                                    continue
                                            conn.commit()
                                        logger.info(f"Enhanced metadata processed: {saved_blocks}/{len(blocks)} blocks")
                                    else:
                                        logger.warning(f"No blocks created by EnhancedVnLegalSplitter for source: {file_id}")
                                else:
                                    logger.warning(f"No text extracted for splitting: {file_id}")
                            else:
                                logger.warning(f"Document processing failed for source: {file_id}")
                        else:
                            logger.warning(f"File path not found for file_id: {file_id}")
                    else:
                        logger.warning(f"File info not found for file_id: {file_id}")
                except Exception as e:
                    logger.error(f"Auto metadata processing failed for source {file_id}: {e}")
            
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
            file_info = db_manager.get_source(source_id)
            if not file_info:
                return jsonify({'success': False, 'error': 'Source not found'}), 404
            
            # Delete physical file
            file_path = normalize_file_path(file_info['file_path'])
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_path}: {e}")
            
            # Delete from database
            db_manager.delete_source(source_id)
            
            logger.info(f"Source deleted successfully: {file_info['filename']}")
            return jsonify({'success': True, 'message': 'Source deleted successfully'})
            
        except Exception as e:
            logger.exception(f"Failed to delete source {source_id}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/sources/<source_id>/generate-metadata', methods=['POST'])
    def generate_metadata(source_id: str) -> Union[Response, tuple]:
        """Generate metadata blocks for a source file"""
        try:
            print(f"\n{'='*60}")
            print(f"[START] Metadata generation requested")
            print(f"  - Source ID: {source_id}")
            print(f"{'='*60}")
            logger.info(f"Manual metadata generation requested for source: {source_id}")
            
            # Get source info from database
            file_info = db_manager.get_source(source_id)
            if not file_info:
                logger.warning(f"File info not found for file_id: {source_id}")
                return jsonify({'success': False, 'error': 'Source not found'}), 404
            
            # Normalize path from database (handle Windows paths in Docker)
            raw_path = file_info['file_path']
            file_path = normalize_file_path(raw_path)
            
            if not file_path.exists():
                logger.warning(f"File path not found for file_id: {source_id}, tried: {file_path}, original: {raw_path}")
                return jsonify({'success': False, 'error': f'File not found: {file_path}'}), 404
            
            # Process the file to extract metadata using enhanced modules
            from .utils import process_document_simple
            from src.core.document_splitter import EnhancedVnLegalSplitter
            from src.core.category_classifier import classify_by_filename
            
            # Process document
            result = process_document_simple(
                str(file_path),
                options={'ocr_enabled': config.OCR_ENABLED}
            )
            
            if result and result.get('success'):
                # Get extracted content
                text_for_split = result.get('cleaned_text') or result.get('raw_text') or ''
                if not text_for_split:
                    return jsonify({'success': False, 'error': 'No content could be extracted from the file'}), 400
                
                # Use EnhancedVnLegalSplitter to create proper blocks
                print(f"[PROCESS] Starting document processing...")
                print(f"  - File: {file_info.get('filename', 'unknown')}")
                print(f"  - Text length: {len(text_for_split)}")
                splitter = EnhancedVnLegalSplitter(use_llm=True)  # Enable LLM for title generation
                filename = file_info.get('filename', '')
                
                # Split document into legal blocks
                blocks = splitter.split_document(text_for_split, filename)
                print(f"[PROCESS] Document split into {len(blocks)} blocks")
                
                if blocks:
                    # Clear existing metadata blocks for this source
                    with db_manager.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM metadata_blocks WHERE doc_id = ?", (source_id,))
                        
                        # Save new blocks to database
                        saved_blocks = 0
                        
                        for block in blocks:
                            try:
                                # Use category classifier for better categorization
                                final_category = classify_by_filename(filename)
                                
                                cursor.execute("""
                                    INSERT INTO metadata_blocks 
                                    (id, doc_id, department, type_data, category, content, source, date, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                                """, (
                                    str(uuid.uuid4()),
                                    block.doc_id,  # Use actual doc_id from document content, not source_id
                                    block.department,
                                    block.type_data,
                                    final_category,
                                    block.content,
                                    block.source,
                                    block.date
                                ))
                                saved_blocks += 1
                            except Exception as block_error:
                                logger.warning(f"Failed to save block: {block_error}")
                                continue
                        
                        conn.commit()
                    
                    print(f"\n{'='*60}")
                    print(f"[SUCCESS] Metadata generation completed!")
                    print(f"  - Source ID: {source_id}")
                    print(f"  - Blocks created: {saved_blocks}")
                    print(f"  - Response: 200 OK")
                    print(f"{'='*60}\n")
                    logger.info(f"Manual metadata generation successful: {saved_blocks} blocks created from {len(blocks)} split blocks")
                    return jsonify({
                        'success': True,
                        'message': f'Generated {saved_blocks} metadata blocks',
                        'blocks_count': saved_blocks
                    })
                else:
                    logger.warning(f"No blocks created by EnhancedVnLegalSplitter for source: {source_id}")
                    return jsonify({'success': False, 'error': 'No blocks could be generated from the document'}), 400
            else:
                logger.warning(f"Document processing failed for source: {source_id}")
                return jsonify({'success': False, 'error': 'Failed to process the document'}), 400
                
        except Exception as e:
            logger.error(f"Manual metadata generation failed for source {source_id}: {e}")
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
            file_info = db_manager.get_source(source_id)
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
            
            files = db_manager.list_sources(limit=limit, offset=offset)
            return jsonify({'sources': files, 'limit': limit, 'offset': offset})
        except Exception as e:
            logger.exception("Failed to list sources")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/sources/<source_id>/info', methods=['GET'])
    def get_source_info(source_id: str) -> Union[Response, tuple]:
        """Get source file info for display"""
        try:
            # Get file info from database
            file_info = db_manager.get_source(source_id)
            if not file_info:
                return jsonify({'success': False, 'error': 'Source not found'}), 404
            
            file_path = normalize_file_path(file_info['file_path'])
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
    def get_source_content(source_id: str):
        """Serve source file content directly, with optional Markdown->HTML render."""
        try:
            logger.info(f"[NEW ROUTE] Getting content for source: {source_id}")

            # 1) DB lookup
            file_info = db_manager.get_source(source_id)
            if not file_info:
                logger.error(f"Source not found: {source_id}")
                return jsonify({'success': False, 'error': 'Source not found'}), 404

            # Normalize path from database (handle Windows paths in Docker)
            raw_path = file_info['file_path']
            file_path = normalize_file_path(raw_path)
            file_type = file_info.get('file_type', '').lower().strip()

            # 2) Path safety: chặn traversal - improved check
            # Normalize both paths for comparison
            safe_base_normalized = SAFE_BASE_DIR.resolve()
            
            # Try to normalize file_path, but handle errors gracefully
            try:
                file_path_normalized = file_path.resolve()
            except (OSError, RuntimeError) as e:
                # If resolve fails, try using filename directly from UPLOAD_FOLDER
                logger.warning(f"Could not resolve path {file_path}, trying filename lookup: {e}")
                filename = Path(raw_path).name
                file_path = config.UPLOAD_FOLDER / filename
                try:
                    file_path_normalized = file_path.resolve()
                except (OSError, RuntimeError):
                    file_path_normalized = file_path  # Use as-is if resolve still fails
            
            # Check if file is within safe base directory using relative path
            try:
                relative = file_path_normalized.relative_to(safe_base_normalized)
                # Check for path traversal (.. in relative path means it's outside)
                if '..' in str(relative):
                    logger.error(f"Path traversal detected: {file_path_normalized}")
                    return jsonify({'success': False, 'error': 'Forbidden'}), 403
            except ValueError:
                # Not a subpath, check if it's the same directory or a direct file in uploads
                if file_path_normalized.parent != safe_base_normalized and file_path_normalized != safe_base_normalized:
                    # Try one more check: if filename matches and exists in UPLOAD_FOLDER
                    filename = file_path_normalized.name if hasattr(file_path_normalized, 'name') else Path(str(file_path_normalized)).name
                    alt_path = safe_base_normalized / filename
                    if alt_path.exists():
                        logger.info(f"Using alternative path: {alt_path}")
                        file_path = alt_path
                        file_path_normalized = alt_path
                    else:
                        logger.error(f"Unsafe path access blocked: {file_path_normalized} (safe_base: {safe_base_normalized})")
                        return jsonify({'success': False, 'error': 'Forbidden'}), 403

            if not file_path.exists():
                logger.error(f"File not found on disk: {file_path}")
                return jsonify({'success': False, 'error': 'File not found on disk'}), 404

            logger.info(f"Serving {file_type} at {file_path}")

            # 3) PDF: trả trực tiếp để nhúng iframe
            if file_type == 'pdf':
                return send_file(
                    str(file_path),
                    as_attachment=False,
                    mimetype=MIME_MAP['pdf'],
                    conditional=True,        # ETag/If-Modified-Since
                    download_name=file_path.name
                )

            # 4) Markdown/text: hai mode
            #    - render=html => convert sang HTML và trả text/html
            #    - render=raw (mặc định) => trả đúng text/markdown hoặc text/plain
            if file_type in ['txt', 'md', 'markdown', 'html', 'xml', 'json']:
                render_mode = request.args.get('render', 'raw').lower()

                # Chọn MIME hợp lệ
                mimetype = MIME_MAP.get(file_type) or mimetypes.guess_type(file_path.name)[0] or 'text/plain; charset=utf-8'

                # HTML file: nếu render=raw thì serve trực tiếp, nếu render=html cũng thế
                if file_type == 'html':
                    return send_file(
                        str(file_path),
                        as_attachment=False,
                        mimetype=mimetype,
                        conditional=True,
                        download_name=file_path.name
                    )

                # Đọc nội dung text (an toàn encoding)
                try:
                    content = file_path.read_text(encoding='utf-8', errors='strict')
                except UnicodeDecodeError:
                    # Đừng ngã lăn, thay bằng replace để giữ hiển thị
                    content = file_path.read_text(encoding='utf-8', errors='replace')

                # Markdown -> HTML nếu được yêu cầu
                if file_type in ['md', 'markdown'] and render_mode in ['html', 'view', 'render']:
                    html = markdown.markdown(
                        content,
                        extensions=["extra", "toc", "tables", "fenced_code"]
                    )
                    # Bọc HTML tối giản cho trình duyệt
                    doc = f"""<!doctype html><meta charset="utf-8">
                    <style>
                    html,body{{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial;line-height:1.6}}
                    body{{max-width:900px;margin:40px auto;padding:0 16px}}
                    pre,code{{font-family:ui-monospace,Menlo,Consolas,monospace}}
                    pre{{overflow:auto;padding:12px;border:1px solid #eee;border-radius:8px;background:#fafafa}}
                    table{{border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:6px 10px}}
                    </style>{html}"""
                    resp = Response(doc, mimetype="text/html; charset=utf-8")
                else:
                    # Trả thô: text/markdown hoặc text/plain
                    resp = Response(content, mimetype=mimetype)

                # Cache nhẹ 60s cho đỡ nghẽn
                resp.headers["Cache-Control"] = "public, max-age=60"
                resp.headers["X-Content-Type-Options"] = "nosniff"
                return resp

            # 5) Loại khác: fallback trả file binary inline
            guessed = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'
            logger.warning(f"Unsupported/other file type '{file_type}', serving as {guessed}")
            return send_file(
                str(file_path),
                as_attachment=False,
                mimetype=guessed,
                conditional=True,
                download_name=file_path.name
            )

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
    
    # SPA fallback route - serve index.html for all non-API routes
    @app.route('/web-app/frontend/<path:path>')
    def serve_frontend(path):
        """Serve frontend files with SPA fallback"""
        target = (FRONTEND_DIR / path).resolve()
        if FRONTEND_DIR not in target.parents and target != FRONTEND_DIR:
            return jsonify({'error': 'Forbidden'}), 403
        if target.exists() and target.is_file():
            resp = send_file(str(target))
            resp.headers['Cache-Control'] = 'public, max-age=300'
            return resp
        index_path = (FRONTEND_DIR / "index.html")
        if index_path.exists():
            resp = send_file(str(index_path))
            resp.headers['Cache-Control'] = 'public, max-age=60'
            return resp
        return jsonify({'error': 'Frontend not found'}), 404
    
    @app.route('/web-app/frontend/')
    def serve_frontend_root():
        """Serve frontend root"""
        index_path = (FRONTEND_DIR / "index.html")
        if index_path.exists():
            resp = send_file(str(index_path))
            resp.headers['Cache-Control'] = 'public, max-age=60'
            return resp
        return jsonify({'error': 'Frontend not found'}), 404
    
    # Suppress linter warnings about unused functions
    # These functions are accessed by Flask's routing system via decorators
    _ = (health, supported_formats, process_file, get_result, download_result, 
         list_files, list_results, get_stats, ocr_status, get_config, installation_guide,
         upload_source, delete_source, rename_source, list_sources, get_source_info, get_source_content)
