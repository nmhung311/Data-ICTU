#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Vietnamese Legal Document Splitter

Implements the exact requirements:
1. Split Vietnamese legal documents into Điều/Khoản/Điểm blocks
2. Extract "source" from exact keyword matches ("Căn cứ...", "Theo...", "Điều...", "Khoản...", "Điểm...", "Nơi nhận...")
3. Generate category using rule-based classification
4. Preserve original content in "## Nội dung" section without any modifications
5. Use LLM only for generating keywords from document titles
"""

import re
import os
import logging
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import LLM service for keyword generation
from .llm_service import get_llm_service
# Import department and category classifiers
from .department_classifier import extract_department_from_content
from .category_classifier import classify_by_content
# Import Căn cứ handler
from .can_cu_handler import create_can_cu_blocks, build_can_cu_markdown
# Import Quyết định handler
from .quyet_dinh_handler import extract_quyet_dinh_block, find_quyet_dinh_span, extract_quyet_dinh_to_noi_nhan, extract_quyet_dinh_section, build_quyet_dinh_markdown_with_content
# Import keyword generator
from .keyword_generator import KeywordGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# Helper functions for folding and finding spans
# =========================

def fold(s: str) -> str:
    """
    Chuẩn hóa so khớp: hạ chữ thường, bỏ dấu tiếng Việt, nén whitespace.
    Dùng để TÌM VỊ TRÍ, sau đó cắt từ bản gốc để giữ nguyên văn.
    """
    s_nfkd = unicodedata.normalize("NFKD", s)
    s_no_accent = "".join(ch for ch in s_nfkd if not unicodedata.combining(ch))
    s_low = s_no_accent.lower()
    # nén khoảng trắng cho regex chấm câu lởm khởm
    s_low = re.sub(r"\s+", " ", s_low)
    return s_low

def _original_index_from_folded(original: str, folded: str, idx_in_folded: int) -> int:
    """
    Map chỉ số từ chuỗi folded về chuỗi gốc.
    Chiến lược: đi song song đến idx_in_folded, đếm ký tự không phải khoảng trắng/dấu hợp lệ.
    Đủ chính xác để cắt biên khu vực lớn. Không phải byte-perfect nhưng ok cho lát cắt.
    """
    # Xây map tích lũy
    o, f = 0, 0
    while o < len(original) and f < idx_in_folded:
        # tiến từng ký tự folded bằng cách bỏ dấu/normalize của original[o]
        ch = original[o]
        ch_fold = fold(ch)
        if ch_fold:
            f += len(ch_fold)
        else:
            # ký tự chỉ dấu, không đóng góp
            pass
        o += 1
    return o

@dataclass
class LegalBlock:
    """A legal document block matching test.md output format."""
    doc_id: str
    department: str
    type_data: str
    category: str
    date: str
    source: str
    content: str

class EnhancedVnLegalSplitter:
    """
    Enhanced Vietnamese Legal Document Splitter
    
    Follows the exact specifications from the user's prompt:
    - Deterministic splitting by Vietnamese legal hierarchy
    - Exact source extraction from keyword matches
    - LLM-based category assignment with fixed taxonomy
    - Preserves original content verbatim
    """
    
    # Hàm __init__ này dùng để khởi tạo đối tượng EnhancedVnLegalSplitter, 
    # cấu hình các thuộc tính như khóa API, bật/tắt LLM, khởi tạo dịch vụ LLM (OpenAI GPT-4o),
    # biên dịch trước các regex để nhận diện các thành phần trong văn bản luật.
    def __init__(self, api_key: Optional[str] = None, use_llm: bool = True):
        """
        Hàm khởi tạo (constructor) cho splitter.
        Chức năng:
            - Lưu thông tin API key (nếu có) để gọi LLM (OpenAI GPT-4o).
            - Cài đặt bật/tắt chế độ sử dụng LLM (use_llm).
            - Khởi tạo/cấu hình dịch vụ LLM nếu bật.
            - Biên dịch tất cả regex để trích xuất các phần của văn bản luật: số hiệu, ngày tháng, điều, khoản, căn cứ, chương, footer, v.v.
        Args:
            api_key: OpenAI API Key để dùng GPT-4o (tùy chọn)
            use_llm: Có sử dụng LLM (OpenAI GPT-4o) hay chỉ rule-based (default: True)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.use_llm = use_llm
        # Note: keyword caching được xử lý bởi KeywordGenerator, không cần cache riêng ở đây

        # Khởi tạo dịch vụ LLM nếu bật
        if self.use_llm:
            self.llm_service = get_llm_service(self.api_key)
            self.llm_enabled = self.llm_service.is_available()
            if self.llm_enabled:
                logger.info("OpenAI LLM service (GPT-4o) đã khởi tạo thành công")
            else:
                logger.warning("OpenAI LLM service không có sẵn, sẽ sử dụng rule-based")
        else:
            self.llm_service = None
            self.llm_enabled = False
            logger.info("Sử dụng chế độ rule-based (không dùng LLM)")
        
        # Khởi tạo keyword generator
        self.keyword_generator = KeywordGenerator(self.llm_service, self.use_llm)

        # Biên dịch các regex pattern phục vụ cho tách, nhận diện các thành phần luật
        self.patterns = {
            # Nhận diện header: số hiệu, ngày tháng
            'doc_id': re.compile(r'(?mi)^\s*Số\s*:\s*([A-Z0-9ĐƠƯ/.\-–&]+)\s*$'),
            'date_location': re.compile(r'([^,]+),\s*ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', re.IGNORECASE),
            'date_simple': re.compile(r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', re.IGNORECASE),

            # Pattern nhận diện hệ thống phân cấp Điều khoản/Chương/Căn cứ
            'legal_basis_start': re.compile(r'^\s*[\*\-\•]?\s*[\*\-\•]?\s*(Căn\s*cứ|Can\s*cu|Theo)\b.*$', re.MULTILINE | re.IGNORECASE),
            'article': re.compile(r'(?m)^\s*\*?\*?Điều\s+([0-9]+)\.?\*?\*?\s*(.*)$', re.IGNORECASE),
            'clause': re.compile(r'(?m)^\s*Khoản\s+([0-9]+)\.?\s*(.*)$', re.IGNORECASE),
            'point_a': re.compile(r'(?m)^\s*([a-zA-Z])\)\s+', re.MULTILINE),
            'point_b': re.compile(r'(?m)^\s*Điểm\s+([a-zA-Z])\s*[:\.]?\s*', re.MULTILINE | re.IGNORECASE),

            # Pattern đặc biệt cho "như sau:"
            'nhu_sau_pattern': re.compile(r'(?i)(?m)^(.*?)\s*("?như\s+sau"?)\s*:\s*(.*)$', re.MULTILINE),
            'nhu_sau_simple': re.compile(r'(?i)(?m)^(.*?)\s*("?như\s+sau"?)\s*:\s*$', re.MULTILINE),

            # "Quy trình" với "Bước n:"
            'quy_trinh_pattern': re.compile(r'(?i)Quy\s*trình', re.MULTILINE),
            'buoc_pattern': re.compile(r'(?i)[\-\s]*Bước\s+[0-9]+', re.MULTILINE),

            # Nhận diện "Chương", số thứ tự...
            'chuong_pattern': re.compile(r'(?im)^\s*Chương\s+[IVXLC\d]+\b.*', re.MULTILINE),
            'khoan_number_pattern': re.compile(r'(?m)^\s*([0-9]+)\.\s+', re.MULTILINE),

            # Nhận diện footer
            'footer': re.compile(r'^(Nơi nhận|KT\.\s*HIỆU TRƯỞNG|HIỆU TRƯỞNG)', re.MULTILINE | re.IGNORECASE),
        }
    # Hàm này dùng để tách một văn bản pháp lý thành các block theo hệ thống phân cấp (như Điều, Khoản, Chương...) của pháp luật Việt Nam.
    # Kết quả trả về là một danh sách các đối tượng LegalBlock, mỗi block chứa metadata, loại, nguồn, nội dung được chuẩn hóa để sử dụng về sau.
    def split_document(self, text: str, filename: str = "") -> List[LegalBlock]:
        """
        Hàm này dùng để tách một văn bản pháp lý thành các block theo hệ thống phân cấp (như Điều, Khoản, Chương...) của pháp luật Việt Nam,
        đồng thời gán metadata cho từng block và chuẩn hóa nội dung.
        
        Args:
            text: Văn bản gốc (dạng chuỗi)
            filename: Tên file chứa tài liệu (tùy chọn)
            
        Returns:
            Danh sách các LegalBlock, mỗi block chứa chính xác các trường metadata cần thiết
        """
        if not text or not text.strip():
            return []

        # Chuẩn hóa dòng xuống dòng lên
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Trích xuất metadata chung của toàn văn bản (như số hiệu, ngày ban hành, v.v.)
        doc_metadata = self._extract_document_metadata(text)

        blocks = []

        # Extract blocks Căn cứ và Quyết định trước
        can_cu_blocks = create_can_cu_blocks(text)
        qd_content = extract_quyet_dinh_block(text)
        
        # Tách văn bản thành các phần theo hệ cấp (Điều, Khoản, Chương, v.v.)
        sections = self._split_by_hierarchy(text)
        
        # Tạo list sections với Căn cứ và Quyết định ở đầu
        all_sections = []
        if can_cu_blocks:
            all_sections.extend(can_cu_blocks)
        if qd_content and qd_content.strip():
            all_sections.append(('quyet_dinh', qd_content, {'name': 'Quyết định'}))
        all_sections.extend(sections)
        
        logger.info(f"Document split: {len(can_cu_blocks)} Căn cứ blocks, 1 Quyết định, {len(sections)} Điều/Khoản")

        for idx, (section_type, section_content, section_info) in enumerate(all_sections):
            if not section_content.strip():
                continue

            # Tạo metadata riêng cho block này dựa trên phân cấp và nội dung
            metadata = self._create_block_metadata(
                doc_metadata, section_type, section_info, section_content
            )

            # Phân loại category cho block (rule-based)
            metadata['category'] = classify_by_content(section_content)

            # Chuẩn hóa nội dung để tạo ra block sạch
            standardized_content = self._create_standardized_content(section_content.strip(), metadata['source'])

            # Tạo LegalBlock
            block = LegalBlock(
                doc_id=metadata['doc_id'],
                department=metadata['department'],
                type_data=metadata['type_data'],
                category=metadata['category'],
                date=metadata['date'],
                source=metadata['source'],
                content=standardized_content
            )
            
            blocks.append(block)

        logger.info(f"Document processed: {len(blocks)} blocks created")
        return blocks

    def _extract_document_metadata(self, text: str) -> Dict[str, Any]:
        """Extract document-level metadata (doc_id, date) with yyyy-mm-dd format."""
        # Extract doc_id - try multiple patterns như trong document_splitter.py
        doc_id = ""
        
        # Pattern 1: "Số: 429/QĐ-ĐHCNT&TT" - format chuẩn nhất, chỉ tìm ở đầu văn bản
        doc_id_match = self.patterns['doc_id'].search(text[:2000])  # Chỉ tìm trong 2000 ký tự đầu
        if doc_id_match:
            doc_id = doc_id_match.group(1).strip()
        
        # Pattern 2: Format: số/QĐ-cơ quan (ví dụ: 1893/QĐ-ĐHTN)
        if not doc_id:
            qd_pattern = re.search(r'(\d+\/QĐ-[A-ZĐƠƯ&]+)', text, re.IGNORECASE)
            if qd_pattern:
                doc_id = qd_pattern.group(1)
        
        # Pattern 3: Format: số/TT-cơ quan (ví dụ: 48/2020/TT-BGDĐT)
        if not doc_id:
            tt_pattern = re.search(r'(\d+\/\d+\/TT-[A-ZĐƠƯ&]+)', text, re.IGNORECASE)
            if tt_pattern:
                doc_id = tt_pattern.group(1)
        
        # Pattern 4: Format: số/NĐ-CP (ví dụ: 11/2015/NĐ-CP)
        if not doc_id:
            nd_pattern = re.search(r'(\d+\/\d+\/NĐ-CP)', text, re.IGNORECASE)
            if nd_pattern:
                doc_id = nd_pattern.group(1)
        
        # Pattern 5: Format: số/NQ-HĐT (ví dụ: 15/NQ-HĐT)
        if not doc_id:
            nq_pattern = re.search(r'(\d+\/NQ-[A-ZĐƠƯ&]+)', text, re.IGNORECASE)
            if nq_pattern:
                doc_id = nq_pattern.group(1)
        
        # Pattern 6: QD-DHCNTT&TT pattern (fallback)
        if not doc_id:
            qd_match = re.search(r'(QD-DHCNTT[&]?TT)', text, re.IGNORECASE)
            if qd_match:
                doc_id = qd_match.group(1)
        
        # Pattern 7: General number patterns (last resort)
        if not doc_id:
            number_match = re.search(r'(\d+[\/\-]\d+[\/\-]?\d*[\/\-]?[A-ZĐƠƯ\-&]*)', text, re.IGNORECASE)
            if number_match:
                doc_id = number_match.group(1)
        
        # Extract date with yyyy-mm-dd format (4 digits year)
        date_str = ""
        date_match = self.patterns['date_location'].search(text)
        if date_match:
            _, day, month, year = date_match.groups()
            try:
                # Ensure year is 4 digits
                year_int = int(year)
                if year_int < 100:  # Convert 2-digit year to 4-digit
                    year_int += 2000 if year_int < 50 else 1900
                date_obj = datetime(year_int, int(month), int(day))
                date_str = date_obj.strftime('%Y-%m-%d')  # yyyy-mm-dd format
            except ValueError:
                pass
        
        if not date_str:
            simple_date_match = self.patterns['date_simple'].search(text)
            if simple_date_match:
                day, month, year = simple_date_match.groups()
                try:
                    # Ensure year is 4 digits
                    year_int = int(year)
                    if year_int < 100:  # Convert 2-digit year to 4-digit
                        year_int += 2000 if year_int < 50 else 1900
                    date_obj = datetime(year_int, int(month), int(day))
                    date_str = date_obj.strftime('%Y-%m-%d')  # yyyy-mm-dd format
                except ValueError:
                    pass
        
        return {
            'doc_id': doc_id,
            'department': self._extract_department_from_content(text),
            'date': date_str
        }
    
    def _extract_department_from_content(self, text: str) -> str:
        """Extract department from content based on keywords."""
        # Sử dụng hàm từ department_classifier module
        return extract_department_from_content(text)
    
    def _create_standardized_content(self, content: str, source: str) -> str:
        """Create standardized content - Remove markdown characters."""
        # Remove ** from content
        cleaned_content = content.replace('**', '')
        return cleaned_content.strip()
    
    def _extract_document_title_from_blocks(self, blocks: List[LegalBlock]) -> str:
        """
        Extract document title from blocks.
        Ưu tiên từ block "Quyết định" (từ Điều 1), sau đó từ block đầu tiên.
        
        Args:
            blocks: List of LegalBlock objects
            
        Returns:
            Document title string (empty if not found)
        """
        # Ưu tiên tìm từ block "Quyết định"
        for block in blocks:
            if block.source == "Quyết định":
                lines = block.content.split('\n')[:20]
                for line in lines:
                    if re.search(r'Điều\s*1[.:]', line, re.IGNORECASE):
                        quoted_match = re.search(r'["""]([^"""]+)["""]', line)
                        if quoted_match:
                            return quoted_match.group(1).strip()
        
        # Thử lấy từ block đầu tiên
        if blocks and blocks[0].content:
            lines = blocks[0].content.split('\n')[:10]
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and len(line) < 200:
                    if not line.startswith(('Căn cứ', 'Theo', 'QUYẾT ĐỊNH', 'Điều', 'Khoản', 'Chương')):
                        return line
        
        return ""
    
    def _create_title_for_block(self, content: str, source: str, section_type: str = "") -> str:
        """Create title for any block using LLM based on content and source type."""
        try:
            # Try to find document title in the content
            lines = content.split('\n')
            document_title = ""
            
            # FIRST: SPECIAL CASE for "Quyết định" source - extract document title from Điều 1 quoted text
            if source == "Quyết định":
                # Look for Điều 1 which contains the regulation name in quotes
                for line in lines[:50]:  # Check first 50 lines to find Điều 1
                    if re.search(r'Điều\s*1[.:]', line, re.IGNORECASE):
                        # Extract quoted text
                        quoted_match = re.search(r'["""]([^"""]+)["""]', line)
                        if quoted_match:
                            document_title = quoted_match.group(1)
                            break
            
            # SECOND: Look for document title (usually at the beginning) - skip if already found
            if not document_title:
                for line in lines[:10]:  # Check first 10 lines
                    line = line.strip()
                    if line and not line.startswith(('Căn cứ', 'Theo', 'QUYẾT ĐỊNH', 'Điều', 'Khoản', 'Chương')):
                        # This might be the document title
                        if len(line) > 10 and len(line) < 200:  # Reasonable title length
                            document_title = line
                            break
            
            if not document_title:
                # Fallback: Try to find any meaningful text in first few lines
                for line in lines[:5]:
                    line = line.strip()
                    if line and len(line) > 10 and len(line) < 200:
                        document_title = line
                        break
                # Final fallback
                if not document_title:
                    document_title = "Quy định"
            
            # SKIP keyword generation if document_title is from "Căn cứ" block
            # Only create keyword from actual document titles, not from "Căn cứ" lines
            if document_title.startswith('Căn cứ') or 'Căn cứ' in document_title:
                document_title = ""  # Reset to empty to skip LLM call
            
            # Get document keyword using keyword_generator (will be cached after first call)
            # Only call if we have a real document title, not "Căn cứ"
            keyword = self._get_document_keyword(document_title) if document_title else ""
            
            # SPECIAL CASE: For "Điều" source, extract article title from content first
            article_title_for_llm = document_title
            if source.startswith("Điều"):
                article_num = source.split()[1] if len(source.split()) > 1 else ""
                # Look for "Điều X. Title" pattern in content
                for line in lines[:5]:
                    line_stripped = line.strip()
                    title_match = re.search(r'(?:\*\*)?Điều\s+\d+\.\s*(.+?)(?:\s*\*\*)?$', line_stripped, re.IGNORECASE)
                    if title_match:
                        article_title_for_llm = title_match.group(1).strip()
                        article_title_for_llm = re.sub(r'[,;\.]$', '', article_title_for_llm).strip()
                        break
            
            # Fallback: create title based on source type
            # Nếu có keyword thì thêm "liên quan đến {keyword}", không thì bỏ
            suffix = f" liên quan đến {keyword}" if keyword else ""
            
            if source == "Căn cứ":
                return "Các căn cứ pháp lý để ban hành quy định" + suffix
            elif source == "Quyết định":
                return "Quyết định ban hành quy định" + suffix
            elif source.startswith("Điều"):
                # Check if this is "Điều X, Khoản Y" format (has comma and "Khoản")
                has_khoan = ',' in source and 'Khoản' in source
                
                if has_khoan:
                    # For "Điều X, Khoản Y": just return source with suffix
                    return f"{source}{suffix}"
                
                # For "Điều X" standalone: extract article number and title from content
                article_num = source.split()[1] if len(source.split()) > 1 else ""
                
                # Try to find article title in content (format: "Điều X. Title" or "Điều X. Title,")
                article_title = ""
                for line in lines[:5]:  # Check first 5 lines
                    line_stripped = line.strip()
                    # Match patterns like: "Điều 1. Title" or "**Điều 1. Title**"
                    title_match = re.search(r'(?:\*\*)?Điều\s+\d+\.\s*(.+?)(?:\s*\*\*)?$', line_stripped, re.IGNORECASE)
                    if title_match:
                        article_title = title_match.group(1).strip()
                        # Clean up common endings
                        article_title = re.sub(r'[,;\.]$', '', article_title).strip()
                        break
                
                # Default: Use full article title
                if article_title:
                    return f"Điều {article_num}. {article_title}{suffix}"
                
                # If no title found, just use number
                if article_num:
                    return f"Điều {article_num}{suffix}"
                return f"{source}{suffix}"
            elif source.startswith("Chương"):
                return f"{source}{suffix}"
            elif source.startswith("Phụ lục"):
                return f"{source}{suffix}"
            else:
                return f"{source}{suffix}"
            
        except Exception as e:
            logger.warning(f"Error creating title for block: {e}")
            # Return simple title without keyword if error occurs
            return source

    def _get_document_keyword(self, document_title: str) -> str:
        """
        Get document keyword sử dụng KeywordGenerator (tái sử dụng từ keyword_generator.py).
        KeywordGenerator đã có cache, không cần cache riêng ở đây.
        
        Args:
            document_title: The document title
            
        Returns:
            Keyword string
        """
        # Sử dụng trực tiếp keyword_generator.generate_keyword() 
        # (đã có cache và xử lý LLM/fallback bên trong)
        if not document_title or not hasattr(self, 'keyword_generator'):
            return ""
        return self.keyword_generator.generate_keyword(document_title)
    

    def _extract_source_from_content(self, content: str) -> str:
        """Extract source from content based on patterns."""
        content_lower = content.lower()
        
        # Check for specific patterns - prioritize more specific patterns first
        if 'căn cứ' in content_lower:
            return "Căn cứ"
        elif 'điều' in content_lower:
            # Extract article number - highest priority
            article_match = re.search(r'điều\s+(\d+)', content_lower)
            if article_match:
                return f"Điều {article_match.group(1)}"
        elif 'quyết định' in content_lower and 'ban hành' in content_lower:
            return "Quyết định"
        elif 'khoản' in content_lower:
            # Extract article and clause numbers
            article_match = re.search(r'điều\s+(\d+)', content_lower)
            khoan_match = re.search(r'khoản\s+(\d+)', content_lower)
            if article_match and khoan_match:
                return f"Điều {article_match.group(1)}, Khoản {khoan_match.group(1)}"
        elif 'phụ lục' in content_lower:
            # Extract appendix number
            appendix_match = re.search(r'phụ\s+lục\s+(\d+)', content_lower)
            if appendix_match:
                return f"Phụ lục {appendix_match.group(1)}"
        
        return ""
    
    def _is_d1_scope_and_subject(self, title: str) -> bool:
        """Check if Điều 1 title contains both 'phạm vi điều chỉnh' and 'đối tượng áp dụng'."""
        t = title.strip().lower()
        return "phạm vi điều chỉnh" in t and "đối tượng áp dụng" in t

    def _is_scope_only(self, title: str) -> bool:
        """Check if title contains only 'phạm vi điều chỉnh' (not 'đối tượng áp dụng')."""
        t = title.strip().lower()
        return "phạm vi điều chỉnh" in t and "đối tượng áp dụng" not in t

    def _is_subject_only(self, title: str) -> bool:
        """Check if title contains only 'đối tượng áp dụng' (not 'phạm vi điều chỉnh')."""
        t = title.strip().lower()
        return "đối tượng áp dụng" in t and "phạm vi điều chỉnh" not in t

    def _find_dieu_start_point(self, text: str) -> Optional[int]:
        """
        Tìm điểm xuất phát để bắt đầu parse các Điều.
        Các dấu hiệu:
        1. "Phạm vi điều chỉnh" - xuất hiện trong Điều 1
        2. Tìm sau "Nơi nhận" -> "Ký" -> separator "***" -> "## QUY ĐỊNH"
        3. Tìm "NHỮNG QUY ĐỊNH CHUNG"
        4. Tìm "## QUY ĐỊNH" trực tiếp
        """
        lines = text.split('\n')
        
        # Bước 1: Tìm "Phạm vi điều chỉnh" (Ưu tiên cao nhất)
        for i, line in enumerate(lines):
            striped = line.strip()
            if re.search(r"Phạm\s+vi\s+điều\s+chỉnh", striped, re.IGNORECASE):
                # Kiểm tra xem có phải là Điều 1 không
                # Tìm dòng Điều gần nhất trước "Phạm vi điều chỉnh"
                for j in range(i - 5, i + 1):  # Kiểm tra 5 dòng trước
                    if j < 0:
                        continue
                    stripped_j = lines[j].strip()
                    if re.search(r"Điều\s+1", stripped_j, re.IGNORECASE):
                        return j
                # Nếu không tìm thấy Điều 1 trước đó, trả về dòng hiện tại
                return i
        
        # Bước 2: Tìm "Nơi nhận"
        noi_nhan_line = None
        for i, line in enumerate(lines):
            striped = line.strip()
            if re.search(r"Nơi\s+nhận\s*:", striped, re.IGNORECASE):
                noi_nhan_line = i
                break
        
        # Bước 3: Tìm "Ký" sau "Nơi nhận"
        if noi_nhan_line is not None:
            for i in range(noi_nhan_line + 1, len(lines)):
                striped = lines[i].strip()
                if re.search(r"\(Ký\b|Ký\s+.*đóng\s+dấu|Ký\s+và\s+đóng\s+dấu", striped, re.IGNORECASE):
                    # Tìm separator "***" sau Ký
                    for j in range(i + 1, len(lines)):
                        stripped = lines[j].strip()
                        if re.search(r"^\*\*\*", stripped):
                            # Tìm "## QUY ĐỊNH" sau separator
                            for k in range(j + 1, len(lines)):
                                stripped2 = lines[k].strip()
                                if re.search(r"^##\s+QUY\s+ĐỊNH", stripped2, re.IGNORECASE):
                                    # Điểm xuất phát là sau dòng ## QUY ĐỊNH (có thể là Chương hoặc Điều)
                                    return k + 1
                            return j + 2  # Trả về sau separator
                    return i + 3  # Trả về sau Ký
        
        # Bước 4: Tìm trực tiếp "NHỮNG QUY ĐỊNH CHUNG"
        for i, line in enumerate(lines):
            striped = line.strip()
            if re.search(r"NHỮNG\s+QUY\s+ĐỊNH\s+CHUNG", striped, re.IGNORECASE):
                return i + 1
        
        # Bước 5: Tìm trực tiếp "## QUY ĐỊNH"
        for i, line in enumerate(lines):
            striped = line.strip()
            if re.search(r"^##\s+QUY\s+ĐỊNH", striped, re.IGNORECASE):
                return i + 1
        
        return None

    def _split_by_hierarchy(self, text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Split text by Vietnamese legal hierarchy (Điều, Khoản, Chương, etc.)
        Các block Căn cứ và Quyết định đã được xử lý riêng ở split_document()
        
        CHỈ parse các Điều từ điểm xuất phát (sau khi gặp "Nơi nhận", "NHỮNG QUY ĐỊNH CHUNG", "ký", "QUY ĐỊNH")
        """
        sections: List[Tuple[str, str, Dict[str, Any]]] = []

        # Tìm điểm xuất phát (start point) dựa trên các từ khóa
        start_point_line = self._find_dieu_start_point(text)
        if start_point_line is None:
            start_point_line = 0
        
        # Parse các Điều/Khoản/Cường/Phụ lục
        # Tìm vùng Quyết định để khóa parse Điều bên trong
        qd_start_char, qd_end_char, qd_start_line, qd_end_line = find_quyet_dinh_span(text)

        lines = text.split('\n')
        n = len(lines)

        # Helper: kiểm tra dòng có nằm trong vùng Quyết định
        def in_qd_region(line_idx: int) -> bool:
            return (qd_start_line is not None and qd_end_line is not None
                    and qd_start_line <= line_idx <= qd_end_line)

        # Parse các section còn lại (CHƯƠNG, ĐIỀU), bỏ qua vùng Quyết định
        # Bắt đầu từ điểm xuất phát
        i = start_point_line
        
        while i < n:
            raw_line = lines[i]
            line = raw_line.strip()

            # Skip rỗng
            if not line:
                i += 1
                continue

            # Nếu dòng này ở trong vùng Quyết định, bỏ qua
            if in_qd_region(i):
                i += 1
                continue

            # 1) CHƯƠNG - bỏ qua, không parse làm section riêng, chỉ dùng để chia văn bản
            m_chuong = re.search(
                r'(?im)^\s*\*\*(Chương|Chuong)\s+([IVXLC\d]+)\s*[—\-]?\s*(.*?)\*\*', line
            )
            if m_chuong:
                i += 1
                continue

            # 3) ĐIỀU - Chỉ parse nếu:
            #   - KHÔNG có block Quyết định (free mode) HOẶC
            #   - Có block Quyết định VÀ đang SAU nó (i > qd_end_line)
            is_after_qd = (qd_start_line is not None) and (i > qd_end_line)
            is_free_mode = (qd_start_line is None)  # không có QĐ trong tài liệu
            
            if is_free_mode or is_after_qd:
                m_article = (
                    re.search(r'(?im)^\s*\*\*(Điều|Dieu)\s+(\d+)\s*[—\-\.]?\s*(.*?)\*\*', line) or
                    re.search(r'(?im)^\s*\*\*(Điều|Dieu)\s+(\d+)\s*\.?\s*(.*?)$', line) or
                    re.search(r'(?im)^\s*(Điều|Dieu)\s+(\d+)\s*\.?\s*(.*?)$', line)
                )
                if m_article:
                    content, end_pos = self._extract_article_from_position(lines, i, text)
                    if content:
                        article_num = m_article.group(2)
                        article_title = (m_article.group(3) or "").strip()

                        if self._should_split_article_by_khoan(article_title):
                            khoan_sections = self._split_article_by_khoan(content, article_num, article_title)
                            sections.extend(khoan_sections)
                        else:
                            sections.append((
                                'article',
                                content,
                                {'article_num': article_num, 'article_title': article_title}
                            ))
                        i = end_pos + 1
                        continue

            i += 1

        return sections
    
  
    
    def _extract_article_from_position(self, lines: List[str], start_pos: int, full_text: str) -> Tuple[str, int]:
        """Extract article content starting from given position."""
        article_lines = []
        i = start_pos
        
        # Add the article line itself
        article_lines.append(lines[start_pos])
        i += 1
        
        # Look for next legal boundary
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip Chương lines, markdown headings, and separators
            if (re.search(r'^#+\s*', line) or  # Skip any markdown heading (#, ##, ###)
                re.search(r'#+\s*(CHƯƠNG|Chương)', line, re.IGNORECASE) or
                re.search(r'^\s*\*\*(CHƯƠNG|Chương)\s+', line, re.IGNORECASE) or
                re.search(r'^\s*(CHƯƠNG|Chương)\s+[IVXLC\d]+', line, re.IGNORECASE) or
                re.search(r'^_{5,}$|^=+$|^\-+$', line)):
                i += 1
                continue
            
            # Stop at next legal boundaries - support multiple patterns
            if (re.search(r'^\s*\*\*Điều\s+\d+', line, re.IGNORECASE) or
                re.search(r'^\s*Điều\s+\d+', line, re.IGNORECASE) or
                re.search(r'^\s*\*\*Chương\s+[IVXLC\d]+', line, re.IGNORECASE) or
                re.search(r'^\s*Chương\s+[IVXLC\d]+', line, re.IGNORECASE) or
                re.search(r'^\s*\*\*Phụ\s+lục\s+\d+', line, re.IGNORECASE) or
                re.search(r'^\s*Phụ\s+lục\s+\d+', line, re.IGNORECASE) or
                re.search(r'^\s*Nơi\s+nhận', line, re.IGNORECASE)):
                break
            
            article_lines.append(lines[i])
            i += 1
        
        content = '\n'.join(article_lines) if article_lines else ""
        
        # Clean content: remove any Chương-related lines
        clean_lines = []
        for line in content.split('\n'):
            stripped = line.strip()
            # Skip if contains Chương patterns, separators, or markdown headings
            if (re.search(r'^#+\s*', stripped) or  # Skip any markdown heading
               re.search(r'^\s*\*\*(CHƯƠNG|Chương)', stripped, re.IGNORECASE) or
               re.search(r'^\s*(CHƯƠNG|Chương)\s+[IVXLC\d]+', stripped, re.IGNORECASE) or
               re.search(r'^_{5,}$|^=+$|^\-+$', stripped) or
               # Skip chapter titles (all caps lines >= 20 chars, likely Vietnamese chapter titles)
               # Allow punctuation and Vietnamese accents
               (re.match(r'^[A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ\s,.;:!\?]+$', stripped) and len(stripped) > 20)):
                continue
            clean_lines.append(line)
        
        content = '\n'.join(clean_lines) if clean_lines else ""
        return content, i - 1  # Return the last processed position
    
    def _extract_phu_luc_from_position(self, lines: List[str], start_pos: int) -> Tuple[str, int]:
        """Extract Phụ lục content starting from given position."""
        phu_luc_lines = []
        i = start_pos
        
        # Add the Phụ lục line itself
        phu_luc_lines.append(lines[start_pos])
        i += 1
        
        # Look for next legal boundary
        while i < len(lines):
            line = lines[i].strip()
            
            # Stop at next legal boundaries
            if (re.search(r'^\s*\*\*Phụ\s+lục\s+[0-9]+', line, re.IGNORECASE) or
                re.search(r'^\s*\*\*Điều\s+\d+', line, re.IGNORECASE) or
                re.search(r'^\s*\*\*Chương\s+[IVXLC\d]+', line, re.IGNORECASE) or
                re.search(r'^\s*Nơi\s+nhận', line, re.IGNORECASE)):
                break
            
            phu_luc_lines.append(lines[i])
            i += 1
        
        content = '\n'.join(phu_luc_lines) if phu_luc_lines else ""
        return content, i - 1  # Return the last processed position
    
    def _extract_chuong_from_position(self, lines: List[str], start_pos: int) -> Tuple[str, int]:
        """Extract Chương content starting from given position."""
        chuong_lines = []
        i = start_pos
        
        # Add the Chương line itself
        chuong_lines.append(lines[start_pos])
        i += 1
        
        # Look for next legal boundary
        while i < len(lines):
            line = lines[i].strip()
            
            # Stop at next legal boundaries
            if (re.search(r'^\s*\*\*Chương\s+[IVXLC\d]+', line, re.IGNORECASE) or
                re.search(r'^\s*\*\*Điều\s+\d+', line, re.IGNORECASE) or
                re.search(r'^\s*\*\*Phụ\s+lục\s+\d+', line, re.IGNORECASE) or
                re.search(r'\*\s*Nơi\s+nhận', line, re.IGNORECASE)):
                break
            
            chuong_lines.append(lines[i])
            i += 1
        
        content = '\n'.join(chuong_lines) if chuong_lines else ""
        return content, i - 1  # Return the last processed position
    

    def _should_split_article_by_khoan(self, article_title: str) -> bool:
        """Check if article should be split by khoan based on title."""
        # Special cases for Điều 1
        if self._is_d1_scope_and_subject(article_title) or self._is_scope_only(article_title):
            return False
        
        # Check if title contains "và" - this is the key rule
        return "và" in article_title
    
    def _split_article_by_khoan(self, article_content: str, article_num: str, article_title: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Split article by khoan following exact rule."""
        sections = []
        
        # If article is too short (< 600 chars), keep as whole article
        if len(article_content) < 600:
            sections.append(('article', article_content, {
                'article_num': article_num,
                'article_title': article_title
            }))
            return sections
        
        # Split by numbered clauses (1., 2., 3., etc.)
        khoan_matches = list(re.finditer(r'(?m)^\s*([0-9]+)\.\s+(.*)$', article_content))
        
        if khoan_matches:
            for i, match in enumerate(khoan_matches):
                khoan_num = match.group(1)
                
                # Determine clause boundaries
                start_pos = match.start()
                if i + 1 < len(khoan_matches):
                    end_pos = khoan_matches[i + 1].start()
                else:
                    end_pos = len(article_content)
                
                khoan_text = article_content[start_pos:end_pos].strip()
                
                if khoan_text:
                    sections.append(('khoan', khoan_text, {
                        'article_num': article_num,
                        'article_title': article_title,
                        'khoan_num': khoan_num
                    }))
        else:
            # No numbered clauses found, keep as whole article
            sections.append(('article', article_content, {
                'article_num': article_num,
                'article_title': article_title
            }))
        
        return sections
    
    def _create_block_metadata(self, doc_metadata: Dict[str, Any], 
                             section_type: str, section_info: Dict[str, Any], 
                             content: str) -> Dict[str, Any]:
        """Create metadata for a block following exact format from test.md."""
        # Determine source based on section_type first (priority)
        source = ""

        if section_type == 'legal_basis':
            source = "Căn cứ"
        elif section_type == 'quyet_dinh':
            source = "Quyết định"
        elif section_type == 'article':
            article_num = section_info.get('article_num', '')
            source = f"Điều {article_num}"
        elif section_type == 'khoan':
            # Format: Điều X, Khoản Y (theo test.md)
            article_num = section_info.get('article_num', '')
            khoan_num = section_info.get('khoan_num', '')
            source = f"Điều {article_num}, Khoản {khoan_num}"
        elif section_type == 'subsection':
            # subsection = numbered 1., 2., ... nhưng khác nhánh 'khoan'
            article_num = section_info.get('article_num', '')
            num = section_info.get('subsection_num', '')
            source = f"Điều {article_num}, Khoản {num}"
        elif section_type == 'khoan_number_clause':
            # chuyển "Khoản n của Điều X" sang format thống nhất
            src = section_info.get('khoan_number_source', '')  # e.g., "Khoản 3 của Điều 8"
            m = re.search(r'Khoản\s+(\d+).*?Điều\s+(\d+)', src)
            if m:
                khoan_num, article_num = m.group(1), m.group(2)
                source = f"Điều {article_num}, Khoản {khoan_num}"
            else:
                # fallback
                article_num = section_info.get('article_num', '')
                khoan_num = section_info.get('khoan_num', '')
                source = f"Điều {article_num}, Khoản {khoan_num}"
        elif section_type == 'point':
            article_num = section_info.get('article_num', '')
            clause_num = section_info.get('clause_num', '') or section_info.get('khoan_num', '')
            point_letter = section_info.get('point_letter', '')
            # Format: Điều X, Khoản Y, Điểm Z (theo test.md)
            source = f"Điều {article_num}, Khoản {clause_num}, Điểm {point_letter}"
        elif section_type in ('nhu_sau_clause', 'nhu_sau_article'):
            # giữ Điều/Khoản nếu có, còn lại fallback Điều X
            article_num = section_info.get('article_num', '')
            clause_num = section_info.get('clause_num', '')
            source = f"Điều {article_num}" + (f", Khoản {clause_num}" if clause_num else "")
        elif section_type in ('quy_trinh_clause', 'quy_trinh_article'):
            article_num = section_info.get('article_num', '')
            clause_num = section_info.get('clause_num', '')
            source = f"Điều {article_num}" + (f", Khoản {clause_num}" if clause_num else "")
        elif section_type == 'chuong':
            # Format: Chương X — tiêu đề
            chuong_source = section_info.get('source', '')
            source = chuong_source
        elif section_type == 'phu_luc':
            # Format: Phụ lục X
            phu_luc_num = section_info.get('phu_luc_num', '')
            source = f"Phụ lục {phu_luc_num}"
        
        # If section_type logic failed, fallback to content analysis
        if not source:
            source = self._extract_source_from_content(content)
        
        if not source:
            source = "Unknown"
        
        metadata = {
            'doc_id': doc_metadata.get('doc_id', ''),
            'department': doc_metadata.get('department', 'Training Department'),
            'type_data': 'markdown',
            'category': section_info.get('category', 'training_and_regulations'),  # Use category from section_info if available
            'date': doc_metadata.get('date', ''),
            'source': source
        }
        return metadata
    def to_markdown(self, blocks: List[LegalBlock]) -> str:
        """
        Convert blocks to Markdown format with metadata fields.
        Sử dụng build_can_cu_markdown() và build_quyet_dinh_markdown() cho các block tương ứng.
        
        Returns:
            Markdown string with blocks separated by ---
        """
        if not blocks:
            return ""
        
        # Extract document title từ blocks để generate keyword
        # Sử dụng helper method để tái sử dụng code
        document_title = self._extract_document_title_from_blocks(blocks)
        
        # Generate keyword sử dụng keyword_generator (tái sử dụng từ KeywordGenerator)
        keyword = ""
        if document_title:
            # Skip keyword generation nếu title bắt đầu bằng "Căn cứ"
            if not (document_title.startswith('Căn cứ') or 'Căn cứ' in document_title):
                self.keyword_generator.reset_cache()
                keyword = self.keyword_generator.generate_keyword(document_title)
                logger.info(f"Generated keyword '{keyword}' from document title: {document_title}")
        
        markdown_lines = []
        
        for i, block in enumerate(blocks):
            # Thêm separator trước mỗi block (trừ block đầu tiên)
            # Đặc biệt: thêm nhiều line breaks trước các Điều mới (xuất phát trang mới)
            if i > 0:
                # Kiểm tra nếu là block "Điều" (bắt đầu một điều mới)
                if block.source.startswith("Điều"):
                    # Xuất phát trang mới - thêm 2 dòng trống trước separator
                    markdown_lines.append("")
                    markdown_lines.append("")
                    markdown_lines.append("---")
                    markdown_lines.append("")
                else:
                    # Các block khác - chỉ 1 dòng trống
                    markdown_lines.append("")
                    markdown_lines.append("---")
                    markdown_lines.append("")
            
            # Xử lý đặc biệt cho block "Căn cứ" và "Quyết định"
            if block.source == "Căn cứ":
                metadata_dict = {
                    'doc_id': block.doc_id,
                    'department': block.department,
                    'type_data': block.type_data,
                    'category': block.category,
                    'date': block.date
                }
                # Sử dụng build_can_cu_markdown với keyword và content
                block_markdown = build_can_cu_markdown(metadata_dict, keyword, block.content)
                markdown_lines.append(block_markdown)
            elif block.source == "Quyết định":
                metadata_dict = {
                    'doc_id': block.doc_id,
                    'department': block.department,
                    'type_data': block.type_data,
                    'category': block.category,
                    'date': block.date
                }
                # Sử dụng build_quyet_dinh_markdown_with_content với keyword và content
                block_markdown = build_quyet_dinh_markdown_with_content(metadata_dict, keyword, block.content)
                markdown_lines.append(block_markdown)
            else:
                # Các block khác: giữ nguyên format cũ
                markdown_lines.append("## Metadata")
                markdown_lines.append(f"- **doc_id:** {block.doc_id}")
                markdown_lines.append(f"- **department:** {block.department}")
                markdown_lines.append(f"- **type_data:** {block.type_data}")
                markdown_lines.append(f"- **category:** {block.category}")
                markdown_lines.append(f"- **date:** {block.date}")
                markdown_lines.append(f"- **source:** {block.source}")
                markdown_lines.append("")
                markdown_lines.append("## Nội dung")
                markdown_lines.append("")
                markdown_lines.append(block.content)
        
        return '\n'.join(markdown_lines)


def split_vietnamese_legal_document(text: str, api_key: Optional[str] = None, filename: str = "", use_llm: bool = True) -> str:
    """
    Convenience function to split Vietnamese legal document.
    
    Args:
        text: Raw document text
        api_key: Optional Google API key for LLM
        filename: Tên file gốc (optional)
        use_llm: Có sử dụng LLM hay không (default: True)
        
    Returns:
        Markdown string with split blocks
    """
    splitter = EnhancedVnLegalSplitter(api_key, use_llm)
    blocks = splitter.split_document(text, filename)
    return splitter.to_markdown(blocks)


