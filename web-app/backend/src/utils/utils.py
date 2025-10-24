#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utils module for Raw2MD Agent Backend
Helper functions and utilities
"""

import io
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Import config for OUTPUT_FOLDER
from .config import config

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

logger = logging.getLogger(__name__)

def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def detect_file_type(filename: str) -> str:
    """Detect file type from filename only (cheap). Use magic/mimetype upstream if needed."""
    if not filename:
        return 'unknown'
    
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    # Document types
    if extension == 'pdf':
        return 'pdf'
    elif extension == 'docx':
        return 'docx'
    elif extension == 'doc':
        return 'doc'
    elif extension in ['html', 'htm']:
        return 'html'
    elif extension == 'txt':
        return 'txt'
    elif extension == 'csv':
        return 'csv'
    elif extension == 'xml':
        return 'xml'
    elif extension == 'json':
        return 'json'
    
    # Image types
    elif extension in ['jpg', 'jpeg', 'png', 'tiff', 'bmp', 'webp']:
        return 'image'
    
    return 'unknown'

def extract_doc_id_from_filename(filename: str) -> Optional[str]:
    """Extract VN-style document ID from filename, e.g. 1323/QĐ-ĐHTN, 35/2014/TTLT-BGDĐT-BTC"""
    if not filename:
        return None
    
    # Remove extension
    name_without_ext = Path(filename).stem
    
    # Common Vietnamese document ID patterns
    patterns = [
        # ví dụ: 35/2014/TTLT-BGDĐT-BTC
        r'(\d{1,5}[/\-_]\d{4}[/\-_][A-ZĐĂÂÊÔƠƯ\-]+(?:-[A-ZĐĂÂÊÔƠƯ]+)*)',
        # ví dụ: 1323/QĐ-ĐHTN
        r'(\d{1,5}[/\-_][A-ZĐĂÂÊÔƠƯ]{1,6}(?:-[A-ZĐĂÂÊÔƠƯ]+)*)',
        # ví dụ: QĐ-ĐHTN-1323
        r'([A-ZĐĂÂÊÔƠƯ]{1,6}(?:-[A-ZĐĂÂÊÔƠƯ]+)*[/\-_]\d{1,5})',
        # ví dụ: 35/2014
        r'(\d{1,5}[/\-_]\d{4})',
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, name_without_ext, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    return None

def get_extractor_local(file_type: str, file_path: str):
    """Local extractor resolver to avoid name collision with raw2md_agent.get_extractor"""
    try:
        if file_type == 'pdf':
            from raw2md_agent.extractors import PDFExtractor
            return PDFExtractor(file_path)
        elif file_type == 'docx':
            from raw2md_agent.extractors import DOCXExtractor
            return DOCXExtractor(file_path)
        elif file_type == 'doc':
            # Legacy .doc not supported by DOCX extractor
            raise ImportError("Legacy .doc not supported by DOCX extractor")
        elif file_type == 'html':
            from raw2md_agent.extractors import HTMLExtractor
            return HTMLExtractor(file_path)
        elif file_type == 'txt':
            from raw2md_agent.extractors import TXTExtractor
            return TXTExtractor(file_path)
        elif file_type == 'csv':
            from raw2md_agent.extractors import CSVExtractor
            return CSVExtractor(file_path)
        elif file_type == 'xml':
            from raw2md_agent.extractors import XMLExtractor
            return XMLExtractor(file_path)
        elif file_type == 'json':
            from raw2md_agent.extractors import JSONExtractor
            return JSONExtractor(file_path)
        elif file_type == 'image':
            from raw2md_agent.extractors import ImageExtractor
            return ImageExtractor(file_path)
        else:
            logger.warning(f"No extractor available for file type: {file_type}")
            return None
    except ImportError as e:
        logger.error(f"Failed to import extractor for {file_type}: {e}")
        return None

def process_document_advanced(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process document using advanced Raw2MD Agent pipeline"""
    try:
        from raw2md_agent import (
            detect_type, clean_text, 
            analyze_document, build_metadata_block, 
            compose_markdown, export_to_md
        )
        
        start_time = time.time()
        
        # Detect file type
        file_type = detect_type(file_path)
        logger.info(f"Detected file type: {file_type}")
        
        # Get extractor using local function
        extractor = get_extractor_local(file_type, file_path)
        if not extractor:
            raise ValueError(f"No extractor available for file type: {file_type}")
        
        # Extract text
        raw_text = extractor.extract() or ""
        logger.info(f"Extracted {len(raw_text)} characters")
        
        # Clean text
        cleaned_text = clean_text(raw_text or "")
        logger.info(f"Cleaned text: {len(cleaned_text)} characters")
        
        # Extract metadata
        metadata = analyze_document(cleaned_text, mode='hybrid') or {}
        logger.info(f"Extracted metadata: {len(metadata)} fields")
        
        # Build markdown
        metadata_block = build_metadata_block(metadata)
        markdown_content = compose_markdown(metadata_block, cleaned_text)
        logger.info(f"Generated markdown: {len(markdown_content)} characters")
        
        # Export to file using config.OUTPUT_FOLDER
        output_dir = str(config.OUTPUT_FOLDER)
        output_path = export_to_md(markdown_content, metadata, output_dir)
        
        processing_time = time.time() - start_time
        
        return {
            'success': True,
            'file_type': file_type,
            'raw_text': raw_text,
            'cleaned_text': cleaned_text,
            'metadata': metadata,
            'markdown_content': markdown_content,
            'output_path': str(output_path) if output_path else None,
            'processing_time': processing_time,
            'stats': {
                'raw_length': len(raw_text),
                'cleaned_length': len(cleaned_text),
                'markdown_length': len(markdown_content),
                'metadata_fields': len(metadata)
            }
        }
        
    except Exception as e:
        logger.exception("Advanced processing failed")
        return {
            'success': False,
            'error': str(e),
            'processing_time': time.time() - start_time if 'start_time' in locals() else 0
        }

def process_document_simple(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process document using simple extraction with fallback methods"""
    try:
        start_time = time.time()
        
        # Import Path here to avoid scope issues
        from pathlib import Path
        
        opts = options or {}
        ocr_enabled = bool(str(opts.get('ocr_enabled', True)).lower() in {'1','true','t','yes','y','on'})
        
        # Detect file type
        file_type = detect_file_type(Path(file_path).name)
        logger.info(f"Simple processing file: {Path(file_path).name}, type: {file_type}, OCR: {ocr_enabled}")
        
        # Try to extract text using available methods
        raw_text = ""
        
        # Method 1: Try PyPDF2 for PDF files
        if file_type == 'pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text_parts = []
                    for page in pdf_reader.pages:
                        text_parts.append(page.extract_text())
                    raw_text = '\n'.join(text_parts)
                logger.info(f"PyPDF2 extracted {len(raw_text)} characters")
            except Exception as e:
                logger.warning(f"PyPDF2 extraction failed: {e}")
        
        # Method 2: Try PyMuPDF (fitz) for PDF files if PyPDF2 failed
        if not raw_text and file_type == 'pdf':
            try:
                import fitz
                doc = fitz.open(file_path)
                text_parts = []
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text_parts.append(page.get_text())
                doc.close()
                raw_text = '\n'.join(text_parts)
                logger.info(f"PyMuPDF extracted {len(raw_text)} characters")
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {e}")
        
        # Method 3: Try basic file reading for text files
        if not raw_text and file_type in ['txt', 'html', 'xml', 'json']:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    raw_text = file.read()
                logger.info(f"File reading extracted {len(raw_text)} characters")
            except Exception as e:
                logger.warning(f"File reading failed: {e}")
        
        # Method 4: Try docx for Word documents
        elif file_type == 'docx':
            try:
                from docx import Document
                doc = Document(file_path)
                raw_text = '\n'.join(p.text for p in doc.paragraphs)
                logger.info(f"python-docx extracted {len(raw_text)} characters")
            except Exception as e:
                logger.warning(f"python-docx extraction failed: {e}")

        elif file_type == 'doc':
            logger.warning("Legacy .doc not supported by python-docx. Consider converting to .docx.")
            # Tùy bạn: gọi mammoth/antiword nếu đã cài, còn không thì để OCR fallback nếu là scan
        
        # OCR nếu được phép
        if ocr_enabled and not raw_text.strip() and file_type in ['pdf','image']:
            try:
                import pytesseract
                from PIL import Image
                if file_type == 'pdf':
                    import fitz
                    doc = fitz.open(file_path)
                    for i in range(doc.page_count):
                        page = doc[i]
                        mat = fitz.Matrix(3.0, 3.0)  # ~300 DPI
                        pix = page.get_pixmap(matrix=mat)
                        img = Image.open(io.BytesIO(pix.tobytes("png")))
                        raw_text += pytesseract.image_to_string(img, lang='vie+eng') + '\n'
                    doc.close()
                else:
                    img = Image.open(file_path)
                    raw_text = pytesseract.image_to_string(img, lang='vie+eng')
                logger.info(f"OCR extracted {len(raw_text)} characters")
            except Exception as e:
                logger.warning(f"OCR extraction failed: {e}")

        # Nếu OCR tắt hoặc vẫn không có text
        if not raw_text.strip():
            if not ocr_enabled and file_type in ['pdf','image']:
                logger.warning("OCR disabled and no text layer found.")
            if not raw_text.strip():
                raw_text = f"[Scanned document - no text extracted]\nFile: {Path(file_path).name}\nType: {file_type}"
        
        # Simple cleaning
        cleaned_text = raw_text.strip()
        
        # Initialize output_path
        output_path = None
        
        # Try metadata extraction with fallback
        metadata = {}
        try:
            # Try EnhancedVnLegalSplitter for metadata extraction
            from src.core.document_splitter import EnhancedVnLegalSplitter
            splitter = EnhancedVnLegalSplitter()
            logger.info(f"Starting EnhancedVnLegalSplitter with text length: {len(cleaned_text)}")
            
            # Extract document metadata first
            doc_metadata = splitter._extract_document_metadata(cleaned_text)
            logger.info(f"Extracted doc_metadata: {doc_metadata}")
            
            blocks = splitter.split_document(cleaned_text)
            logger.info(f"EnhancedVnLegalSplitter returned {len(blocks)} blocks")
            
            if len(blocks) > 1:
                # Use splitter results
                metadata = {
                    'blocks_count': len(blocks),
                    'doc_id': blocks[0].doc_id if blocks else None,
                    'filename': str(Path(file_path).name),  # Convert to string
                    'file_type': file_type,
                    'source': str(Path(file_path).name)  # Convert to string
                }
                
                # Create markdown with blocks
                markdown_parts = []
                for block in blocks:
                    markdown_parts.append(f"---\n## Metadata\n")
                    markdown_parts.append(f"**doc_id:** {block.doc_id}\n")
                    markdown_parts.append(f"**category:** {block.category}\n")
                    markdown_parts.append(f"**source:** {block.source}\n")
                    markdown_parts.append(f"**date:** {block.date}\n")
                    markdown_parts.append(f"**modify:** {block.modify}\n")
                    markdown_parts.append(f"**partial_mod:** {block.partial_mod}\n")
                    markdown_parts.append(f"**data_type:** {block.data_type}\n")
                    markdown_parts.append(f"**amend:** {block.amend}\n")
                    markdown_parts.append(f"## Nội dung\n{block.content}\n")
                
                markdown_content = '\n'.join(markdown_parts)
            else:
                logger.info("EnhancedVnLegalSplitter returned <= 1 blocks, using extracted metadata")
                # Use extracted metadata even if no blocks
                metadata = {
                    'doc_id': doc_metadata.get('doc_id', ''),
                    'category': 'training_and_regulations',
                    'source': str(Path(file_path).name),
                    'date': doc_metadata.get('date', ''),
                    'modify': '',
                    'partial_mod': False,
                    'data_type': 'markdown',
                    'amend': '',
                    'filename': str(Path(file_path).name),
                    'file_type': file_type
                }
                
                # Create simple markdown with extracted metadata
                markdown_content = f"## Metadata\n"
                markdown_content += f"- **doc_id:** {metadata['doc_id']}\n"
                markdown_content += f"- **category:** {metadata['category']}\n"
                markdown_content += f"- **source:** {metadata['source']}\n"
                markdown_content += f"- **date:** {metadata['date']}\n"
                markdown_content += f"- **modify:** {metadata['modify']}\n"
                markdown_content += f"- **partial_mod:** {metadata['partial_mod']}\n"
                markdown_content += f"- **data_type:** {metadata['data_type']}\n"
                markdown_content += f"- **amend:** {metadata['amend']}\n"
                markdown_content += f"\n## Nội dung\n\n{cleaned_text}"
                
                # Lưu file output vào thư mục output/
                output_path = None
                try:
                    import uuid
                    
                    # Tạo tên file output
                    output_filename = f"{uuid.uuid4()}.md"
                    output_path = config.OUTPUT_FOLDER / output_filename
                    
                    # Đảm bảo thư mục output tồn tại
                    config.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
                    
                    # Lưu file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    
                    logger.info(f"Saved output to: {output_path}")
                    
                except Exception as save_error:
                    logger.warning(f"Failed to save output file: {save_error}")
                    output_path = None
                
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
            # Fallback metadata
            doc_id = extract_doc_id_from_filename(str(Path(file_path).name))
            metadata = {
                'doc_id': doc_id,
                'filename': str(Path(file_path).name),  # Convert to string
                'file_type': file_type,
                'source': str(Path(file_path).name)  # Convert to string
            }
            
            # Simple markdown
            markdown_content = f"# {metadata.get('doc_id', 'Document')}\n\n{cleaned_text}"
        
        processing_time = time.time() - start_time
        
        return {
            'success': True,
            'file_type': file_type,
            'raw_text': raw_text,
            'cleaned_text': cleaned_text,
            'metadata': metadata,
            'markdown_content': markdown_content,
            'output_path': str(output_path) if 'output_path' in locals() and output_path else None,
            'processing_time': processing_time,
            'stats': {
                'raw_length': len(raw_text),
                'cleaned_length': len(cleaned_text),
                'markdown_length': len(markdown_content),
                'metadata_fields': len(metadata),
                'blocks_count': metadata.get('blocks_count', 1)
            }
        }
        
    except Exception as e:
        logger.error(f"Simple processing failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'processing_time': time.time() - start_time if 'start_time' in locals() else 0
        }

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float /= 1024.0
        i += 1
    
    return f"{size_float:.1f} {size_names[i]}"

def validate_file_upload(file, max_size_mb: int, allowed_extensions: set) -> Dict[str, Any]:
    """Validate uploaded file"""
    if not file or not file.filename:
        return {'valid': False, 'error': 'No file provided'}
    
    # Check file extension
    if not allowed_file(file.filename, allowed_extensions):
        return {
            'valid': False, 
            'error': f'File type not allowed. Allowed types: {", ".join(sorted(allowed_extensions))}'
        }
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return {
            'valid': False,
            'error': f'File too large. Maximum size: {max_size_mb}MB'
        }
    
    return {
        'valid': True,
        'file_size': file_size,
        'file_size_formatted': format_file_size(file_size)
    }
