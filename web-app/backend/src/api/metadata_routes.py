#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metadata API routes for Raw2MD Agent Backend
Handles metadata processing and retrieval
"""

import os
import logging
import uuid
from typing import Union, Dict, Any, List
from pathlib import Path
from flask import Flask, request, jsonify, Response

from ..core.document_splitter import EnhancedVnLegalSplitter, LegalBlock
from ..core.category_classifier import classify_category_from_filename
from ..utils.config import config
from ..utils.database import DatabaseManager

logger = logging.getLogger(__name__)

def register_metadata_routes(app: Flask, db_manager: DatabaseManager):
    """Register metadata-related routes"""
    
    @app.route('/api/metadata', methods=['GET'])
    def get_all_metadata():
        """Get all metadata blocks"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, doc_id, data_type, category, date, source, content, confidence, created_at
                    FROM metadata_blocks 
                    ORDER BY created_at DESC
                """)
                
                rows = cursor.fetchall()
                blocks = []
                
                for row in rows:
                    blocks.append({
                        'id': row[0],
                        'doc_id': row[1],
                        'data_type': row[2],
                        'category': row[3],
                        'date': row[4],
                        'source': row[5],
                        'content': row[6],
                        'confidence': row[7],
                        'created_at': row[8]
                    })
                
                return jsonify({
                    'success': True,
                    'blocks': blocks,
                    'total': len(blocks)
                })
                
        except Exception as e:
            logger.error(f"Error getting metadata blocks: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/sources/<source_id>/process-metadata', methods=['POST'])
    def process_source_metadata(source_id: str):
        """Process a source file into metadata blocks"""
        try:
            # Get source info from database
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, filename, file_path, file_type, created_at
                    FROM sources 
                    WHERE id = ?
                """, (source_id,))
                
                source_row = cursor.fetchone()
                if not source_row:
                    return jsonify({
                        'success': False,
                        'error': 'Source not found'
                    }), 404
                
                source_info = {
                    'id': source_row[0],
                    'filename': source_row[1],
                    'file_path': source_row[2],
                    'file_type': source_row[3],
                    'created_at': source_row[4]
                }
            
            # Check if file exists
            file_path = Path(source_info['file_path'])
            if not file_path.exists():
                return jsonify({
                    'success': False,
                    'error': 'File not found on disk'
                }), 404
            
            # Process file with document splitter
            splitter = EnhancedVnLegalSplitter()
            
            # Read file content
            if source_info['file_type'] == 'pdf':
                # For PDF, we need to extract text first
                # This is a simplified version - in production you'd use proper PDF extraction
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    # For now, we'll create a mock content
                    content_text = f"[PDF Content from {source_info['filename']}]"
                except Exception as e:
                    logger.error(f"Error reading PDF file: {e}")
                    content_text = f"[Error reading PDF: {source_info['filename']}]"
            else:
                # For text files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_text = f.read()
                except Exception as e:
                    logger.error(f"Error reading file: {e}")
                    content_text = f"[Error reading file: {source_info['filename']}]"
            
            # Split document into blocks
            blocks = splitter.split_document(
                content_text, 
                source_info['filename']
            )
            
            # Save blocks to database
            saved_blocks = []
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear existing blocks for this source
                cursor.execute("DELETE FROM metadata_blocks WHERE doc_id = ?", (source_id,))
                
                for block in blocks:
                    block_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO metadata_blocks 
                        (id, doc_id, data_type, category, date, source, content, confidence, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        block_id,
                        source_id,
                        block.data_type,
                        block.category,
                        block.date,
                        block.source,
                        block.content,
                        block.confidence
                    ))
                    
                    saved_blocks.append({
                        'id': block_id,
                        'doc_id': source_id,
                        'data_type': block.data_type,
                        'category': block.category,
                        'date': block.date,
                        'source': block.source,
                        'content': block.content,
                        'confidence': block.confidence
                    })
                
                conn.commit()
            
            return jsonify({
                'success': True,
                'blocks': saved_blocks,
                'total': len(saved_blocks),
                'message': f'Processed {len(saved_blocks)} metadata blocks'
            })
            
        except Exception as e:
            logger.error(f"Error processing metadata for source {source_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/metadata/<block_id>', methods=['GET'])
    def get_metadata_block(block_id: str):
        """Get a specific metadata block"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, doc_id, data_type, category, date, source, content, confidence, created_at
                    FROM metadata_blocks 
                    WHERE id = ?
                """, (block_id,))
                
                row = cursor.fetchone()
                if not row:
                    return jsonify({
                        'success': False,
                        'error': 'Metadata block not found'
                    }), 404
                
                block = {
                    'id': row[0],
                    'doc_id': row[1],
                    'data_type': row[2],
                    'category': row[3],
                    'date': row[4],
                    'source': row[5],
                    'content': row[6],
                    'confidence': row[7],
                    'created_at': row[8]
                }
                
                return jsonify({
                    'success': True,
                    'block': block
                })
                
        except Exception as e:
            logger.error(f"Error getting metadata block {block_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/metadata/<block_id>', methods=['DELETE'])
    def delete_metadata_block(block_id: str):
        """Delete a metadata block"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM metadata_blocks WHERE id = ?", (block_id,))
                
                if cursor.rowcount == 0:
                    return jsonify({
                        'success': False,
                        'error': 'Metadata block not found'
                    }), 404
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Metadata block deleted successfully'
                })
                
        except Exception as e:
            logger.error(f"Error deleting metadata block {block_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
