#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metadata API routes for Raw2MD Agent Backend
Handles metadata processing and retrieval
"""

import os
import re
import logging
import uuid
from typing import Union, Dict, Any, List
from pathlib import Path
from flask import Flask, request, jsonify, Response

from ..core.document_splitter import EnhancedVnLegalSplitter, LegalBlock
from ..core.category_classifier import classify_by_filename
from ..core.can_cu_handler import build_can_cu_markdown
from ..core.quyet_dinh_handler import build_quyet_dinh_markdown_with_content
from ..core.keyword_generator import KeywordGenerator
from ..core.llm_service import get_llm_service
from ..utils.config import config
from ..utils.database import DatabaseManager

logger = logging.getLogger(__name__)

def generate_markdown_export(blocks: List[Dict[str, Any]]) -> str:
    """
    Generate markdown content following test.md format.
    Sử dụng build_can_cu_markdown() và build_quyet_dinh_markdown_with_content() cho các block tương ứng.
    """
    if not blocks:
        return ""
    
    # Extract document title từ blocks để generate keyword
    document_title = ""
    keyword = ""
    
    # Tìm document title từ block "Quyết định" hoặc block đầu tiên
    for block in blocks:
        source = block.get('source', '')
        content = block.get('content', '')
        
        if source == "Quyết định":
            lines = content.split('\n')[:30]
            for line in lines:
                # Tìm Điều 1 và extract title từ quoted text hoặc text sau dấu chấm
                if re.search(r'Điều\s*1[.:]', line, re.IGNORECASE):
                    # Thử extract từ quoted text trước
                    quoted_match = re.search(r'["""]([^"""]+)["""]', line)
                    if quoted_match:
                        document_title = quoted_match.group(1).strip()
                        break
                    else:
                        # Nếu không có quoted text, lấy text sau "Điều 1." đến hết hoặc đến dấu chấm
                        match = re.search(r'Điều\s*1[.:]\s*(.+?)(?:\.$|$)', line, re.IGNORECASE)
                        if match:
                            title_text = match.group(1).strip()
                            # Lọc bỏ các từ thừa như "Ban hành kèm theo Quyết định này"
                            title_text = re.sub(r'^Ban hành kèm theo Quyết định này\s+', '', title_text, flags=re.IGNORECASE)
                            title_text = re.sub(r'^Quy định\s+', '', title_text, flags=re.IGNORECASE)
                            if len(title_text) > 20:  # Đủ dài để là title
                                document_title = title_text
                                break
        elif not document_title and content:
            lines = content.split('\n')[:10]
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and len(line) < 200:
                    if not line.startswith(('Căn cứ', 'Theo', 'QUYẾT ĐỊNH', 'Điều', 'Khoản', 'Chương')):
                        document_title = line
                        break
        
        if document_title:
            break
    
    # Generate keyword nếu có document title
    if document_title:
        import os
        api_key = os.getenv('OPENAI_API_KEY')
        llm_service = get_llm_service(api_key)
        keyword_gen = KeywordGenerator(llm_service, use_llm=True)
        keyword_gen.reset_cache()
        # Skip nếu title bắt đầu bằng "Căn cứ"
        if not (document_title.startswith('Căn cứ') or 'Căn cứ' in document_title):
            keyword = keyword_gen.generate_keyword(document_title)
            logger.info(f"Generated keyword '{keyword}' from document title: {document_title}")
    
    markdown_lines = []
    
    for i, block in enumerate(blocks):
        # Add separator between blocks (except for first block)
        if i > 0:
            markdown_lines.append("")
            markdown_lines.append("---")
            markdown_lines.append("")
        
        source = block.get('source', '')
        
        # Xử lý đặc biệt cho block "Căn cứ" và "Quyết định"
        if source == "Căn cứ":
            metadata_dict = {
                'doc_id': block.get('doc_id', ''),
                'department': block.get('department', ''),
                'type_data': block.get('type_data', 'markdown'),
                'category': block.get('category', ''),
                'date': block.get('date', '')
            }
            content_body = block.get('content', '')
            # Sử dụng build_can_cu_markdown với keyword và content
            block_markdown = build_can_cu_markdown(metadata_dict, keyword, content_body)
            markdown_lines.append(block_markdown)
        elif source == "Quyết định":
            metadata_dict = {
                'doc_id': block.get('doc_id', ''),
                'department': block.get('department', ''),
                'type_data': block.get('type_data', 'markdown'),
                'category': block.get('category', ''),
                'date': block.get('date', '')
            }
            content_body = block.get('content', '')
            # Sử dụng build_quyet_dinh_markdown_with_content với keyword và content
            block_markdown = build_quyet_dinh_markdown_with_content(metadata_dict, keyword, content_body)
            markdown_lines.append(block_markdown)
        else:
            # Các block khác: giữ nguyên format cũ
            markdown_lines.append("## Metadata")
            markdown_lines.append(f"- **doc_id**: {block.get('doc_id', 'N/A')}")
            markdown_lines.append(f"- **department**: {block.get('department', 'N/A')}")
            markdown_lines.append(f"- **type_data**: {block.get('type_data', 'N/A')}")
            markdown_lines.append(f"- **category**: {block.get('category', 'N/A')}")
            markdown_lines.append(f"- **date**: {block.get('date', 'N/A')}")
            markdown_lines.append(f"- **source**: {block.get('source', 'N/A')}")
            markdown_lines.append("")
            markdown_lines.append("## Nội dung")
            markdown_lines.append("")
            markdown_lines.append(block.get('content', ''))
    
    return '\n'.join(markdown_lines)

def register_metadata_routes(app: Flask, db_manager: DatabaseManager):
    """Register metadata-related routes"""
    
    @app.route('/api/metadata', methods=['GET'])
    def get_all_metadata():
        """Get all metadata blocks"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, doc_id, department, type_data, category, date, source, content, created_at
                    FROM metadata_blocks 
                    ORDER BY created_at DESC
                """)
                
                rows = cursor.fetchall()
                blocks = []
                
                for row in rows:
                    blocks.append({
                        'id': row[0],
                        'doc_id': row[1],
                        'department': row[2],
                        'type_data': row[3],
                        'category': row[4],
                        'date': row[5],
                        'source': row[6],
                        'content': row[7],
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
                        (id, doc_id, department, type_data, category, date, source, content, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        block_id,
                        block.doc_id,  # Use actual doc_id from document content
                        block.department,
                        block.type_data,
                        block.category,
                        block.date,
                        block.source,
                        block.content
                    ))
                    
                    saved_blocks.append({
                        'id': block_id,
                        'doc_id': block.doc_id,  # Use actual doc_id from document content
                        'department': block.department,
                        'type_data': block.type_data,
                        'category': block.category,
                        'date': block.date,
                        'source': block.source,
                        'content': block.content
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
                    SELECT id, doc_id, department, type_data, category, date, source, content, created_at
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
                    'department': row[2],
                    'type_data': row[3],
                    'category': row[4],
                    'date': row[5],
                    'source': row[6],
                    'content': row[7],
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

    @app.route('/api/sources/<source_id>/generate-metadata', methods=['POST'])
    def generate_metadata_blocks(source_id: str):
        """Generate metadata blocks for a source file using core technology"""
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
            
            # Read file content based on type
            content_text = ""
            if source_info['file_type'] in ['txt', 'md']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_text = f.read()
                except Exception as e:
                    logger.error(f"Error reading text file: {e}")
                    return jsonify({
                        'success': False,
                        'error': f'Error reading file: {str(e)}'
                    }), 500
            elif source_info['file_type'] == 'pdf':
                # For PDF files, we'll use a simplified approach
                # In production, you'd use proper PDF extraction libraries
                try:
                    # Mock content for PDF - in real implementation, extract text from PDF
                    content_text = f"[PDF Content from {source_info['filename']}]\n\nThis is a placeholder for PDF content extraction."
                except Exception as e:
                    logger.error(f"Error processing PDF file: {e}")
                    return jsonify({
                        'success': False,
                        'error': f'Error processing PDF: {str(e)}'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported file type: {source_info["file_type"]}'
                }), 400
            
            # Use EnhancedVnLegalSplitter to process the document
            splitter = EnhancedVnLegalSplitter(use_llm=True)  # Enable LLM for better results
            
            # Split document into blocks
            blocks = splitter.split_document(
                content_text, 
                source_info['filename']
            )
            
            if not blocks:
                return jsonify({
                    'success': False,
                    'error': 'No metadata blocks generated from document'
                }), 400
            
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
                        (id, doc_id, department, type_data, category, date, source, content, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        block_id,
                        block.doc_id,  # Use actual doc_id from document content
                        block.department,
                        block.type_data,
                        block.category,
                        block.date,
                        block.source,
                        block.content
                    ))
                    
                    saved_blocks.append({
                        'id': block_id,
                        'doc_id': block.doc_id,  # Use actual doc_id from document content
                        'department': block.department,
                        'type_data': block.type_data,
                        'category': block.category,
                        'date': block.date,
                        'source': block.source,
                        'content': block.content
                    })
                
                conn.commit()
            
            return jsonify({
                'success': True,
                'blocks': saved_blocks,
                'total': len(saved_blocks),
                'message': f'Generated {len(saved_blocks)} metadata blocks using AI technology'
            })
            
        except Exception as e:
            logger.error(f"Error generating metadata for source {source_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/metadata', methods=['DELETE'])
    def clear_all_metadata():
        """Clear all metadata blocks from database"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get count before deletion
                cursor.execute("SELECT COUNT(*) FROM metadata_blocks")
                count_before = cursor.fetchone()[0]
                
                if count_before == 0:
                    return jsonify({
                        'success': True,
                        'deleted_count': 0,
                        'message': 'No metadata blocks to delete'
                    })
                
                # Delete all metadata blocks
                cursor.execute("DELETE FROM metadata_blocks")
                
                # Get count after deletion
                cursor.execute("SELECT COUNT(*) FROM metadata_blocks")
                count_after = cursor.fetchone()[0]
                
                conn.commit()
                
                deleted_count = count_before - count_after
                
                logger.info(f"Cleared {deleted_count} metadata blocks from database")
                
                return jsonify({
                    'success': True,
                    'deleted_count': deleted_count,
                    'message': f'Successfully deleted {deleted_count} metadata blocks'
                })
                
        except Exception as e:
            logger.error(f"Error clearing metadata blocks: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/metadata/test', methods=['GET'])
    def test_export_route():
        """Test route to check if export route works"""
        return jsonify({
            'success': True,
            'message': 'Export route is working'
        })

    @app.route('/api/metadata/markdown', methods=['GET'])
    def get_metadata_markdown():
        """Get metadata blocks as formatted markdown string (for frontend display)"""
        try:
            logger.info("GET /api/metadata/markdown requested")
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, doc_id, department, type_data, category, date, source, content, created_at
                    FROM metadata_blocks 
                    ORDER BY created_at ASC
                """)
                
                rows = cursor.fetchall()
                blocks = []
                
                for row in rows:
                    blocks.append({
                        'id': row[0],
                        'doc_id': row[1],
                        'department': row[2],
                        'type_data': row[3],
                        'category': row[4],
                        'date': row[5],
                        'source': row[6],
                        'content': row[7],
                        'created_at': row[8]
                    })
                
                logger.info(f"Found {len(blocks)} metadata blocks")
                
                # Generate markdown using generate_markdown_export() (đã có logic build_can_cu_markdown)
                markdown_content = generate_markdown_export(blocks)
                
                logger.info(f"Generated markdown, length: {len(markdown_content)}")
                
                response = jsonify({
                    'success': True,
                    'markdown': markdown_content,
                    'blocks_count': len(blocks)
                })
                
                # Set content length header
                response.headers['Content-Length'] = str(len(response.data))
                return response
                
        except Exception as e:
            logger.exception(f"Error getting metadata markdown: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/metadata/export', methods=['GET'])
    def export_metadata_to_markdown():
        """Export all metadata blocks to a complete markdown file like test.md"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, doc_id, department, type_data, category, date, source, content, created_at
                    FROM metadata_blocks 
                    ORDER BY created_at ASC
                """)
                
                rows = cursor.fetchall()
                blocks = []
                
                for row in rows:
                    blocks.append({
                        'id': row[0],
                        'doc_id': row[1],
                        'department': row[2],
                        'type_data': row[3],
                        'category': row[4],
                        'date': row[5],
                        'source': row[6],
                        'content': row[7],
                        'created_at': row[8]
                    })
                
                if not blocks:
                    return jsonify({
                        'success': False,
                        'error': 'No metadata blocks found to export'
                    }), 404
                
                # Generate markdown content following test.md format
                markdown_content = generate_markdown_export(blocks)
                
                # Save to file
                output_dir = Path(config.OUTPUT_DIR)
                output_dir.mkdir(exist_ok=True)
                
                filename = f"metadata_export_{uuid.uuid4().hex[:8]}.md"
                output_path = output_dir / filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                logger.info(f"Exported {len(blocks)} metadata blocks to {output_path}")
                
                return jsonify({
                    'success': True,
                    'message': f'Exported {len(blocks)} metadata blocks to markdown file',
                    'filename': filename,
                    'file_path': str(output_path),
                    'blocks_count': len(blocks)
                })
                
        except Exception as e:
            logger.error(f"Error exporting metadata to markdown: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500