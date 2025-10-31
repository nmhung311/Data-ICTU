#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utils module for Raw2MD Agent Backend
Helper functions and utilities
"""

import io
import os
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

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
    elif extension in ['md', 'markdown']:
        return 'md'
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

def _read_pdf_text_pypdf2(file_path: str) -> str:
    """Read PDF text using PyPDF2 with null safety."""
    try:
        import PyPDF2
        text_parts: List[str] = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                txt = page.extract_text() or ""
                if txt:
                    text_parts.append(txt)
        return "\n".join(text_parts).strip()
    except Exception as e:
        logger.debug(f"_read_pdf_text_pypdf2 failed: {e}")
        return ""

def _read_pdf_text_pymupdf(file_path: str) -> str:
    """Read PDF text using PyMuPDF with proper resource cleanup."""
    try:
        import fitz
        text_parts: List[str] = []
        doc = fitz.open(file_path)
        try:
            for i in range(len(doc)):
                page = doc[i]
                text_parts.append(page.get_text("text") or "")
        finally:
            doc.close()
        return "\n".join(text_parts).strip()
    except Exception as e:
        logger.debug(f"_read_pdf_text_pymupdf failed: {e}")
        return ""

def _pdf_has_text_layer(file_path: str) -> bool:
    """Check if PDF has text layer (quick check)."""
    txt = _read_pdf_text_pymupdf(file_path)
    return bool(txt and txt.strip())

def _read_text_file(file_path: str) -> str:
    """Read text file with multiple encoding fallbacks."""
    encodings = ["utf-8", "utf-8-sig", "cp1252"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                return f.read()
        except Exception as e:
            logger.debug(f"read_text_file with {enc} failed: {e}")
    return ""

def _read_docx_text(file_path: str) -> str:
    """Read DOCX text content."""
    try:
        from docx import Document
        doc = Document(file_path)
        parts = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(parts).strip()
    except Exception as e:
        logger.debug(f"_read_docx_text failed: {e}")
        return ""

def _ocr_pdf_with_tesseract(file_path: str, lang: str = "vie+eng", dpi_scale: float = 3.0) -> str:
    """OCR PDF using Tesseract with proper resource management."""
    try:
        import fitz
        from PIL import Image
        import pytesseract

        doc = fitz.open(file_path)
        try:
            ocr_parts: List[str] = []
            for i in range(doc.page_count):
                page = doc[i]
                mat = fitz.Matrix(dpi_scale, dpi_scale)
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_parts.append(pytesseract.image_to_string(img, lang=lang))
            return "\n".join(ocr_parts).strip()
        finally:
            doc.close()
    except Exception as e:
        logger.debug(f"_ocr_pdf_with_tesseract failed: {e}")
        return ""

def _ocr_image_with_tesseract(file_path: str, lang: str = "vie+eng") -> str:
    """OCR image using Tesseract."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(file_path)
        return pytesseract.image_to_string(img, lang=lang).strip()
    except Exception as e:
        logger.debug(f"_ocr_image_with_tesseract failed: {e}")
        return ""

def process_document_simple(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process document using simple extraction with fallback methods."""
    start_time = time.time()
    output_md_path: Optional[Path] = None

    try:
        p = Path(file_path)
        opts = options or {}
        ocr_enabled = str(opts.get("ocr_enabled", True)).lower() in {"1", "true", "t", "yes", "y", "on"}

        file_type = detect_file_type(p.name)
        logger.info(f"[simple] file={p.name} type={file_type} ocr={ocr_enabled}")

        raw_text = ""

        # 1) Text-first for PDF
        if file_type == "pdf":
            raw_text = _read_pdf_text_pypdf2(file_path)
            if not raw_text:
                raw_text = _read_pdf_text_pymupdf(file_path)

        # 2) Plain/text-like files
        if not raw_text and file_type in {"txt", "html", "xml", "json", "md", "markdown"}:
            raw_text = _read_text_file(file_path)

        # 3) DOCX
        if not raw_text and file_type == "docx":
            raw_text = _read_docx_text(file_path)

        # 4) Legacy .doc (khuyến nghị convert)
        if not raw_text and file_type == "doc":
            logger.warning("Legacy .doc not supported. Convert to .docx or enable OCR if scanned.")

        # 5) OCR fallback nếu bật
        if not raw_text and ocr_enabled and file_type in {"pdf", "image"}:
            if file_type == "pdf":
                # Chỉ OCR nếu thực sự không có text layer
                if not _pdf_has_text_layer(file_path):
                    raw_text = _ocr_pdf_with_tesseract(file_path)
                else:
                    # Đã có text layer mà vẫn rỗng nghĩa là extractor fail; thử thêm PyMuPDF lần nữa
                    raw_text = _read_pdf_text_pymupdf(file_path) or raw_text
            else:
                raw_text = _ocr_image_with_tesseract(file_path)

        # 6) Nếu vẫn rỗng, trả về marker có hướng dẫn
        if not raw_text or not raw_text.strip():
            marker = "[Scanned or unsupported document - no text extracted]"
            raw_text = f"{marker}\nFile: {p.name}\nType: {file_type}"

        cleaned_text = raw_text.strip()

        # 7) Metadata & split
        metadata: Dict[str, Any] = {}
        markdown_content = ""
        blocks_count = 1

        try:
            from src.core.document_splitter import EnhancedVnLegalSplitter
            splitter = EnhancedVnLegalSplitter(use_llm=True)  # Enable LLM for title generation

            # Ưu tiên API public: nếu không có, vẫn dùng private nhưng bọc try riêng
            try:
                doc_metadata = splitter.extract_document_metadata(cleaned_text)  # nếu có
            except AttributeError:
                doc_metadata = {}
                try:
                    doc_metadata = splitter._extract_document_metadata(cleaned_text)  # fallback private
                except Exception as e_priv:
                    logger.debug(f"Private metadata extractor failed: {e_priv}")

            logger.info(f"[splitter] text_len={len(cleaned_text)}")
            blocks = splitter.split_document(cleaned_text, p.name)
            blocks_count = len(blocks) if blocks else 0
            logger.info(f"[splitter] blocks={blocks_count}")

            if blocks_count > 1:
                metadata = {
                    "doc_id": getattr(blocks[0], "doc_id", None),
                    "filename": p.name,
                    "file_type": file_type,
                    "source": p.name,
                    "category": getattr(blocks[0], "category", "training_and_regulations"),
                    "date": doc_metadata.get("date") if isinstance(doc_metadata, dict) else None,
                    "department": "Training Department",
                    "type_data": "markdown",
                    "blocks_count": blocks_count,
                }
                markdown_content = splitter.to_markdown(blocks)
            else:
                # Không đủ block, tạo metadata tối thiểu
                fallback_doc_id = (doc_metadata.get("doc_id") if isinstance(doc_metadata, dict) else None) or extract_doc_id_from_filename(p.name)
                metadata = {
                    "doc_id": fallback_doc_id,
                    "filename": p.name,
                    "file_type": file_type,
                    "source": p.name,
                    "category": "training_and_regulations",
                    "date": (doc_metadata.get("date") if isinstance(doc_metadata, dict) else None) or "",
                    "department": "Training Department",
                    "type_data": "markdown",
                    "blocks_count": 1,
                }
                markdown_content = (
                    "## Metadata\n"
                    f"- **doc_id:** {metadata['doc_id']}\n"
                    f"- **department:** {metadata['department']}\n"
                    f"- **type_data:** {metadata['type_data']}\n"
                    f"- **category:** {metadata['category']}\n"
                    f"- **date:** {metadata['date']}\n"
                    f"- **source:** {metadata['source']}\n\n"
                    f"## Nội dung\n\n{cleaned_text}"
                )

        except Exception as split_err:
            logger.warning(f"Metadata/split failed: {split_err}")
            fallback_doc_id = extract_doc_id_from_filename(p.name)
            metadata = {
                "doc_id": fallback_doc_id,
                "filename": p.name,
                "file_type": file_type,
                "source": p.name,
                "category": "training_and_regulations",
                "date": "",
                "data_type": "markdown",
                "blocks_count": 1,
            }
            markdown_content = f"# {fallback_doc_id or 'Document'}\n\n{cleaned_text}"

        # 8) Ghi output MD
        try:
            out_dir: Path = getattr(config, "OUTPUT_FOLDER", Path("output"))
            out_dir.mkdir(parents=True, exist_ok=True)
            output_md_path = out_dir / f"{uuid.uuid4()}.md"
            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            logger.info(f"[simple] saved: {output_md_path}")
        except Exception as save_err:
            logger.warning(f"Save markdown failed: {save_err}")
            output_md_path = None

        processing_time = time.time() - start_time
        return {
            "success": True,
            "file_type": file_type,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "content": cleaned_text,  # Add content field for API compatibility
            "metadata": metadata,
            "markdown_content": markdown_content,
            "output_path": str(output_md_path) if output_md_path else None,
            "processing_time": processing_time,
            "stats": {
                "raw_length": len(raw_text),
                "cleaned_length": len(cleaned_text),
                "markdown_length": len(markdown_content),
                "blocks_count": int(metadata.get("blocks_count", 1)),
                "has_ocr": bool(ocr_enabled),
            },
        }

    except Exception as e:
        logger.error(f"Simple processing failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "processing_time": time.time() - start_time if "start_time" in locals() else 0,
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
