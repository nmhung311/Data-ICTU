#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Vietnamese Legal Document Splitter

Implements the exact requirements from the user's prompt:
1. Split Vietnamese legal documents into Điều/Khoản/Điểm blocks
2. Extract "source" from exact keyword matches ("Căn cứ...", "Theo...", "Điều...", "Khoản...", "Điểm...", "Nơi nhận...")
3. Generate category using LLM with fixed 8-field format
4. Preserve original content in "## Nội dung" section without any modifications
5. Use deterministic temperature=0.0 for LLM calls
"""

import re
import os
import logging
import importlib.util
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import LLM service
from .llm_service import get_llm_service, LLMConfig, GeminiService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LegalBlock:
    """A legal document block with 5 essential metadata fields."""
    doc_id: str
    data_type: str
    category: str
    date: str
    source: str
    content: str
    confidence: float = 0.0  # Độ tin cậy của phân loại

class EnhancedVnLegalSplitter:
    """
    Enhanced Vietnamese Legal Document Splitter
    
    Follows the exact specifications from the user's prompt:
    - Deterministic splitting by Vietnamese legal hierarchy
    - Exact source extraction from keyword matches
    - LLM-based category assignment with fixed taxonomy
    - Preserves original content verbatim
    """
    
    def __init__(self, api_key: Optional[str] = None, use_llm: bool = True):
        """
        Initialize the splitter.
        
        Args:
            api_key: Google API key for Gemini LLM (optional)
            use_llm: Có sử dụng LLM hay không (default: True)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.use_llm = use_llm
        
        # Khởi tạo LLM service
        if self.use_llm:
            self.llm_service = get_llm_service(self.api_key)
            self.llm_enabled = self.llm_service.is_available()
            if self.llm_enabled:
                logger.info("Gemini LLM service đã khởi tạo thành công")
            else:
                logger.warning("Gemini LLM service không có sẵn, sẽ sử dụng rule-based")
        else:
            self.llm_service = None
            self.llm_enabled = False
            logger.info("Sử dụng chế độ rule-based (không dùng LLM)")
        
        # Compile regex patterns as specified in the prompt
        self.patterns = {
            # Document headers - lấy số hiệu văn bản (có thể có hoặc không có **)
            'doc_id': re.compile(r'(?mi)^\s*Số\s*:\s*([A-Z0-9ĐƠƯ/.\-–&]+)\s*$'),
            'date_location': re.compile(r'([^,]+),\s*ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', re.IGNORECASE),
            'date_simple': re.compile(r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', re.IGNORECASE),
            
            # Legal hierarchy patterns - exact from prompt
            'legal_basis_start': re.compile(r'^\s*(Căn\s*cứ|Theo)\b.*$', re.MULTILINE | re.IGNORECASE),
            'article': re.compile(r'(?m)^\s*\*?\*?Điều\s+([0-9]+)\.?\*?\*?\s*(.*)$', re.IGNORECASE),
            'clause': re.compile(r'(?m)^\s*Khoản\s+([0-9]+)\.?\s*(.*)$', re.IGNORECASE),
            'point_a': re.compile(r'(?m)^\s*([a-zA-Z])\)\s+', re.MULTILINE),
            'point_b': re.compile(r'(?m)^\s*Điểm\s+([a-zA-Z])\s*[:\.]?\s*', re.MULTILINE | re.IGNORECASE),
            
            # Special pattern for "như sau:" - NEW ENHANCEMENT
            'nhu_sau_pattern': re.compile(r'(?i)(?m)^(.*?)\s*("?như\s+sau"?)\s*:\s*(.*)$', re.MULTILINE),
            'nhu_sau_simple': re.compile(r'(?i)(?m)^(.*?)\s*("?như\s+sau"?)\s*:\s*$', re.MULTILINE),
            
            # Special pattern for "Quy trình" + "Bước n:" - NEW ENHANCEMENT
            'quy_trinh_pattern': re.compile(r'(?i)Quy\s*trình', re.MULTILINE),
            'buoc_pattern': re.compile(r'(?i)[\-\s]*Bước\s+[0-9]+', re.MULTILINE),
            
            # Special pattern for "Chương" + "Tiêu đề chương" - NEW ENHANCEMENT
            'chuong_pattern': re.compile(r'(?im)^\s*Chương\s+[IVXLC\d]+\b.*', re.MULTILINE),
            'khoan_number_pattern': re.compile(r'(?m)^\s*([0-9]+)\.\s+', re.MULTILINE),
            
            # Footer patterns
            'footer': re.compile(r'^(Nơi nhận|KT\.\s*HIỆU TRƯỞNG|HIỆU TRƯỞNG)', re.MULTILINE | re.IGNORECASE),
        }
        
        # Fixed taxonomy as specified in the prompt
        self.category_taxonomy = [
            'training_and_regulations',
            'academic_affairs', 
            'admissions',
            'finance_and_tuition',
            'examination',
            'postgraduate_training',
            'internship',
            'student_affairs',
            'human_resources',
            'distance_learning'
        ]
    
    def split_document(self, text: str, filename: str = "") -> List[LegalBlock]:
        """
        Split document into legal blocks following Vietnamese hierarchy.
        
        Args:
            text: Raw document text
            filename: Tên file gốc (optional)
            
        Returns:
            List of LegalBlock objects with exact metadata fields
        """
        if not text or not text.strip():
            return []
        
        # Step 0: Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Step 1: Extract document-level metadata
        doc_metadata = self._extract_document_metadata(text)
        
        blocks = []
        
        # Step 2: Split by legal hierarchy hoặc sử dụng LLM
        if self.llm_enabled and self.use_llm:
            # Sử dụng LLM để chia document thông minh
            sections = self._split_with_llm(text, filename, doc_metadata)
        else:
            # Sử dụng rule-based splitting
            sections = self._split_by_hierarchy(text)
        
        for section_type, section_content, section_info in sections:
            if not section_content.strip():
                continue
            
            # Step 3: Create metadata for this block
            metadata = self._create_block_metadata(
                doc_metadata, section_type, section_info, section_content
            )
            
            # Step 4: Generate category using LLM hoặc rule-based
            if self.llm_enabled and self.use_llm:
                category_result = self._generate_category_with_llm_service(
                    metadata, section_content, filename
                )
                metadata['category'] = category_result['category']
                confidence = category_result.get('confidence', 0.0)
            else:
                metadata['category'] = self._generate_category_rule_based(
                    metadata, section_content
                )
                confidence = 0.0
            
            # Create block
            block = LegalBlock(
                doc_id=metadata['doc_id'],
                data_type=metadata['data_type'],
                category=metadata['category'],
                date=metadata['date'],
                source=metadata['source'],
                content=section_content.strip(),
                confidence=confidence
            )
            
            blocks.append(block)
        
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
            'date': date_str
        }
    
    def _cut_noi_nhan_tail(self, text: str) -> str:
        """Cut off 'Nơi nhận' section and everything after it."""
        m = re.search(r'(?mi)^\s*N[ơo]i\s+nh[aă]n\s*:.*', text)
        return text[:m.start()] if m else text
    
    def _extract_document_title(self, text: str) -> str:
        """Extract document title from the text."""
        lines = text.split('\n')
        
        # Look for title patterns in the first few lines
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines (university name, etc.)
            if any(keyword in line.upper() for keyword in ['ĐẠI HỌC', 'TRƯỜNG', 'SỐ:', 'NGÀY']):
                continue
            
            # Look for title patterns
            # Pattern 1: "Về việc..." (most common)
            if line.startswith('Về việc'):
                return line
            
            # Pattern 2: "QUYẾT ĐỊNH" followed by title on next line
            if line.upper() == 'QUYẾT ĐỊNH' and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('Căn cứ'):
                    return next_line
            
            # Pattern 3: Long line that looks like a title (more than 20 chars, not all caps)
            if len(line) > 20 and not line.isupper() and not line.startswith('**'):
                return line
        
        # Fallback: return first non-empty line that's not a header
        for line in lines[:10]:
            line = line.strip()
            if line and not any(keyword in line.upper() for keyword in ['ĐẠI HỌC', 'TRƯỜNG', 'SỐ:', 'NGÀY']):
                return line
        
        return "Tài liệu pháp lý"
    
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

    def _split_by_hierarchy(self, text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Split text by Vietnamese legal hierarchy following new rules:
        1. Group all "Căn cứ" lines into one metadata
        2. Group "QUYẾT ĐỊNH" to "Điều 1" into one metadata
        3. Remove "Nơi nhận" section completely
        4. Split by Điều with new logic
        
        Returns:
            List of (section_type, content, info) tuples
        """
        text = self._cut_noi_nhan_tail(text)  # Cut off "Nơi nhận" tail
        sections = []
        
        # Step 1: Find legal basis section (group all "Căn cứ" lines)
        legal_basis_content = self._extract_legal_basis_grouped(text)
        if legal_basis_content:
            # Extract document title for source
            doc_title = self._extract_document_title(text)
            sections.append(('legal_basis', legal_basis_content, {
                'name': 'Căn cứ',
                'source': doc_title,
                'category': 'source_doc'
            }))
        
        # Step 2: Find "QUYẾT ĐỊNH" section (from QUYẾT ĐỊNH to Điều 1)
        quyet_dinh_content = self._extract_quyet_dinh_section(text)
        if quyet_dinh_content:
            sections.append(('quyet_dinh', quyet_dinh_content, {'name': 'Quyết định'}))
        
        # Step 3: Find articles with new splitting logic
        article_sections = self._extract_articles_with_new_rules(text)
        sections.extend(article_sections)
        
        # Note: Footer section is completely removed as per new rules
        
        return sections
    
    def _split_with_llm(self, text: str, filename: str, doc_metadata: Dict[str, Any]) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Sử dụng LLM để chia document thành các sections thông minh
        
        Args:
            text: Nội dung document
            filename: Tên file gốc
            doc_metadata: Metadata của document
            
        Returns:
            List of (section_type, content, info) tuples
        """
        try:
            # Sử dụng LLM service để chia content
            context = {
                'doc_metadata': doc_metadata,
                'filename': filename
            }
            
            blocks = self.llm_service.split_content_intelligently(text, filename, context)
            
            # Convert LLM blocks thành format của splitter
            sections = []
            for block in blocks:
                section_type = block.get('block_type', 'article')
                content = block.get('content', '')
                metadata = block.get('metadata', {})
                
                # Tạo section_info từ metadata
                section_info = {
                    'name': block.get('title', ''),
                    'source': block.get('source', ''),
                    'category': metadata.get('category', 'training_and_regulations')
                }
                
                # Thêm thông tin cụ thể theo loại block
                if section_type == 'article':
                    # Tìm số điều từ content
                    article_match = re.search(r'Điều\s+(\d+)', content, re.IGNORECASE)
                    if article_match:
                        section_info['article_num'] = article_match.group(1)
                        section_info['article_title'] = content.split('\n')[0] if content else ''
                
                elif section_type == 'khoan':
                    # Tìm số khoản từ content
                    khoan_match = re.search(r'Khoản\s+(\d+)', content, re.IGNORECASE)
                    if khoan_match:
                        section_info['khoan_num'] = khoan_match.group(1)
                
                sections.append((section_type, content, section_info))
            
            logger.info(f"LLM đã chia document thành {len(sections)} sections")
            return sections
            
        except Exception as e:
            logger.warning(f"Lỗi khi sử dụng LLM để chia document: {e}")
            # Fallback về rule-based splitting
            return self._split_by_hierarchy(text)
    
    def _generate_category_with_llm_service(self, metadata: Dict[str, Any], content: str, filename: str = "") -> Dict[str, Any]:
        """
        Sử dụng LLM service để phân loại category
        
        Args:
            metadata: Metadata của block
            content: Nội dung block
            filename: Tên file gốc
            
        Returns:
            Dict với category và confidence
        """
        try:
            context = {
                'metadata': metadata,
                'filename': filename
            }
            
            result = self.llm_service.classify_category(content, filename, context)
            logger.debug(f"LLM phân loại category: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"Lỗi khi sử dụng LLM để phân loại category: {e}")
            return {
                'category': 'training_and_regulations',
                'confidence': 0.0,
                'reasoning': f'Lỗi LLM: {str(e)}'
            }
    
    def _generate_category_rule_based(self, metadata: Dict[str, Any], content: str) -> str:
        """
        Phân loại category dựa trên rules (fallback khi không có LLM)
        
        Args:
            metadata: Metadata của block
            content: Nội dung block
            
        Returns:
            Category string
        """
        content_lower = content.lower()
        
        # Mapping từ khóa -> category
        keyword_mapping = {
            'postgraduate_training': ['tiến sĩ', 'thạc sĩ', 'sau đại học', 'ts', 'ths'],
            'admissions': ['tuyển sinh', 'xét tuyển', 'điều kiện dự tuyển'],
            'finance_and_tuition': ['học phí', 'miễn giảm', 'thu', 'chi', 'quy định phí'],
            'examination': ['kỳ thi', 'thi cử', 'đánh giá', 'kiểm tra'],
            'internship': ['thực tập', 'tttn', 'doanh nghiệp', 'internship'],
            'distance_learning': ['đào tạo từ xa', 'e-learning', 'online', 'qua mạng'],
            'student_affairs': ['công tác sinh viên', 'khen thưởng', 'kỷ luật', 'học bổng', 'rèn luyện'],
            'human_resources': ['tổ chức cán bộ', 'nhân sự', 'cbvc'],
            'academic_affairs': ['phòng đào tạo', 'chương trình học', 'tín chỉ', 'kế hoạch giảng dạy', 'gdtc', 'thể chất', 'quy chế']
        }
        
        # Tìm category khớp đầu tiên
        for category, keywords in keyword_mapping.items():
            for keyword in keywords:
                if keyword in content_lower:
                    logger.debug(f"Rule-based phân loại: '{keyword}' -> '{category}'")
                    return category
        
        # Default
        return 'training_and_regulations'
    
    def _extract_legal_basis_grouped(self, text: str) -> str:
        """Extract all 'Căn cứ' lines grouped into one section, stopping before QUYẾT ĐỊNH."""
        lines = text.split('\n')
        legal_lines = []
        in_legal_basis = False
        
        for line in lines:
            if self.patterns['legal_basis_start'].search(line):
                in_legal_basis = True
                legal_lines.append(line)
            elif in_legal_basis:
                # Stop at QUYẾT ĐỊNH or first article
                if (re.search(r'^\s*QUYẾT\s*ĐỊNH', line, re.IGNORECASE) or 
                    re.search(r'^\s*\*\*Điều\s+\d+', line, re.IGNORECASE)):
                    break
                # Only add lines that are still part of legal basis (not QUYẾT ĐỊNH content)
                if not re.search(r'^\s*\*\*Điều\s+\d+', line, re.IGNORECASE):
                    legal_lines.append(line)
        
        return '\n'.join(legal_lines) if legal_lines else ""
    
    def _extract_quyet_dinh_section(self, text: str) -> str:
        """Extract section from QUYẾT ĐỊNH to Điều 1 (excluding Căn cứ)."""
        lines = text.split('\n')
        quyet_dinh_lines = []
        in_quyet_dinh = False
        
        for line in lines:
            if re.search(r'^\s*QUYẾT\s*ĐỊNH', line, re.IGNORECASE):
                in_quyet_dinh = True
                quyet_dinh_lines.append(line)
            elif in_quyet_dinh:
                # Stop at Căn cứ or first article
                if (self.patterns['legal_basis_start'].search(line) or 
                    re.search(r'^\s*Điều\s+\d+', line, re.IGNORECASE)):
                    break
                quyet_dinh_lines.append(line)
        
        return '\n'.join(quyet_dinh_lines) if quyet_dinh_lines else ""
    
    def _extract_articles_with_new_rules(self, text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Extract articles with new splitting rules based on test.md format:
        - Split by Khoản (numbered clauses) within each Điều
        - Format source as: Điều [số] -> Khoản [số]
        - Handle Chương as separate metadata
        - Handle Phụ lục as separate metadata
        """
        sections = []
        
        # First, find and handle Chương sections
        chuong_sections = self._extract_chuong_sections(text)
        sections.extend(chuong_sections)
        
        # Find all articles
        article_matches = list(self.patterns['article'].finditer(text))
        
        for i, article_match in enumerate(article_matches):
            article_num = article_match.group(1)
            article_title = article_match.group(2).strip()
            
            # Determine end of this article
            start_pos = article_match.start()
            if i + 1 < len(article_matches):
                end_pos = article_matches[i + 1].start()
            else:
                # Look for "Nơi nhận" or "Phụ lục" to stop
                next_boundaries = []
                noi_nhan_match = re.search(r'^\s*Nơi\s+nhận', text[start_pos:], re.MULTILINE | re.IGNORECASE)
                if noi_nhan_match:
                    next_boundaries.append(start_pos + noi_nhan_match.start())
                phu_luc_match = re.search(r'^\s*Phụ\s+lục', text[start_pos:], re.MULTILINE | re.IGNORECASE)
                if phu_luc_match:
                    next_boundaries.append(start_pos + phu_luc_match.start())
                end_pos = min(next_boundaries) if next_boundaries else len(text)
            
            article_text = text[start_pos:end_pos]
            
            # SPECIAL for Điều 1
            if article_num == '1':
                if self._is_d1_scope_and_subject(article_title):
                    # LẤY NGUYÊN KHỐI, KHÔNG CHẺ KHOẢN
                    sections.append(('article', article_text, {
                        'article_num': article_num,
                        'article_title': article_title
                    }))
                    continue
                # Trường hợp Điều 1 "Phạm vi điều chỉnh" và Điều 2 "Đối tượng áp dụng": 
                # để cơ chế mặc định chia theo điều, KHÔNG chia khoản ở Điều 1/2
                if self._is_scope_only(article_title):
                    sections.append(('article', article_text, {
                        'article_num': article_num,
                        'article_title': article_title
                    }))
                    continue
            
            # Với các điều KHÁC: chỉ chẻ theo khoản khi tiêu đề có "và"
            khoan_sections = self._split_by_khoan_clauses(article_text, article_num, article_title)
            sections.extend(khoan_sections)
        
        # Handle Phụ lục sections
        phu_luc_sections = self._extract_phu_luc_sections(text)
        sections.extend(phu_luc_sections)
        
        return sections
    
    def _extract_chuong_sections(self, text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Extract Chương sections as separate metadata."""
        sections = []
        
        # Find all Chương matches
        chuong_matches = list(re.finditer(r'(?im)^\s*\*\*Chương\s+([IVXLC\d]+)\s*—\s*(.*?)\*\*', text))
        
        for match in chuong_matches:
            chuong_num = match.group(1)
            chuong_title = match.group(2).strip()
            
            # Extract the full Chương line
            chuong_line = match.group(0).strip()
            
            sections.append(('chuong', chuong_line, {
                'chuong_num': chuong_num,
                'chuong_title': chuong_title,
                'source': f"Chương {chuong_num} — {chuong_title}"
            }))
        
        return sections
    
    def _split_by_khoan_clauses(self, article_text: str, article_num: str, article_title: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Split article by Khoản following exact rule: if title has 'và' then split by numbered clauses."""
        sections = []
        
        # Không chẻ khoản cho "Đối tượng áp dụng"
        if self._is_subject_only(article_title):
            return [('article', article_text, {
                'article_num': article_num,
                'article_title': article_title
            })]
        
        # Check if article title contains "và" - this is the key rule
        if "và" in article_title:
            # Split by numbered clauses (1., 2., 3., etc.)
            khoan_matches = list(re.finditer(r'(?m)^\s*([0-9]+)\.\s+(.*)$', article_text))
            
            if khoan_matches:
                for i, match in enumerate(khoan_matches):
                    khoan_num = match.group(1)
                    
                    # Determine clause boundaries
                    start_pos = match.start()
                    if i + 1 < len(khoan_matches):
                        end_pos = khoan_matches[i + 1].start()
                    else:
                        # Look for next legal boundary
                        next_boundaries = []
                        
                        # Look for next Điều
                        next_dieu = re.search(r'^\s*Điều\s+\d+', article_text[start_pos:], re.MULTILINE | re.IGNORECASE)
                        if next_dieu:
                            next_boundaries.append(start_pos + next_dieu.start())
                        
                        # Look for next Chương
                        next_chuong = re.search(r'^\s*\*\*Chương\s+[IVXLC\d]+', article_text[start_pos:], re.MULTILINE | re.IGNORECASE)
                        if next_chuong:
                            next_boundaries.append(start_pos + next_chuong.start())
                        
                        # Look for Phụ lục
                        next_phu_luc = re.search(r'^\s*Phụ\s+lục', article_text[start_pos:], re.MULTILINE | re.IGNORECASE)
                        if next_phu_luc:
                            next_boundaries.append(start_pos + next_phu_luc.start())
                        
                        end_pos = min(next_boundaries) if next_boundaries else len(article_text)
                    
                    khoan_text = article_text[start_pos:end_pos].strip()
                    
                    if khoan_text:
                        sections.append(('khoan', khoan_text, {
                            'article_num': article_num,
                            'article_title': article_title,
                            'khoan_num': khoan_num
                        }))
            else:
                # Title has "và" but no numbered clauses found, keep as whole article
                sections.append(('article', article_text, {
                    'article_num': article_num,
                    'article_title': article_title
                }))
        else:
            # Title doesn't have "và", keep as whole article
            sections.append(('article', article_text, {
                'article_num': article_num,
                'article_title': article_title
            }))
        
        return sections
    
    def _extract_phu_luc_sections(self, text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Extract Phụ lục sections as separate metadata."""
        sections = []
        
        # Find Phụ lục matches
        phu_luc_matches = list(re.finditer(r'(?im)^\s*\*\*Phụ\s+lục\s+([0-9]+)\s*—\s*(.*?)\*\*', text))
        
        for match in phu_luc_matches:
            phu_luc_num = match.group(1)
            phu_luc_title = match.group(2).strip()
            
            # Find the start position of this phụ lục
            start_pos = match.start()
            
            # Look for next legal boundary or end of text
            next_boundaries = []
            
            # Look for next Phụ lục
            next_phu_luc = re.search(r'^\s*\*\*Phụ\s+lục\s+[0-9]+', text[start_pos + 1:], re.MULTILINE | re.IGNORECASE)
            if next_phu_luc:
                next_boundaries.append(start_pos + 1 + next_phu_luc.start())
            
            end_pos = min(next_boundaries) if next_boundaries else len(text)
            
            phu_luc_text = text[start_pos:end_pos].strip()
            
            if phu_luc_text:
                sections.append(('phu_luc', phu_luc_text, {
                    'phu_luc_num': phu_luc_num,
                    'phu_luc_title': phu_luc_title,
                    'source': f"Phụ lục {phu_luc_num}"
                }))
        
        return sections
    
    def _handle_other_dieu(self, article_text: str, article_num: str, article_title: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Handle other articles with 'và' splitting logic."""
        sections = []
        
        # Check if title contains "và"
        if "và" in article_title:
            # Split by numbered sub-sections (1., 2., 3., etc.)
            sub_sections = self._split_by_numbered_subsections(article_text, article_num, article_title)
            sections.extend(sub_sections)
        else:
            # Keep as one metadata
            sections.append(('article', article_text, {
                'article_num': article_num,
                'article_title': article_title
            }))
        
        return sections
    
    def _split_by_numbered_subsections(self, article_text: str, article_num: str, article_title: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Split article by numbered sub-sections (1., 2., 3., etc.)."""
        sections = []
        
        # Find all numbered sub-sections
        subsection_matches = list(re.finditer(r'(?m)^\s*([0-9]+)\.\s+(.*)$', article_text))
        
        if subsection_matches:
            for i, match in enumerate(subsection_matches):
                subsection_num = match.group(1)
                subsection_title = match.group(2).strip()
                
                # Determine subsection boundaries
                start_pos = match.start()
                if i + 1 < len(subsection_matches):
                    end_pos = subsection_matches[i + 1].start()
                else:
                    # Look for next legal boundary
                    next_boundaries = []
                    
                    # Look for next Điều
                    next_dieu = re.search(r'^\s*Điều\s+\d+', article_text[start_pos:], re.MULTILINE | re.IGNORECASE)
                    if next_dieu:
                        next_boundaries.append(start_pos + next_dieu.start())
                    
                    # Look for "Nơi nhận"
                    next_noi_nhan = re.search(r'^\s*Nơi\s+nhận', article_text[start_pos:], re.MULTILINE | re.IGNORECASE)
                    if next_noi_nhan:
                        next_boundaries.append(start_pos + next_noi_nhan.start())
                    
                    end_pos = min(next_boundaries) if next_boundaries else len(article_text)
                
                subsection_content = article_text[start_pos:end_pos].strip()
                
                if subsection_content:
                    sections.append(('subsection', subsection_content, {
                        'article_num': article_num,
                        'article_title': article_title,
                        'subsection_num': subsection_num,
                        'subsection_title': subsection_title
                    }))
        else:
            # No numbered subsections, keep as whole article
            sections.append(('article', article_text, {
                'article_num': article_num,
                'article_title': article_title
            }))
        
        return sections

    def _extract_articles(self, text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Extract articles and their sub-sections."""
        sections = []
        
        # Find all articles
        article_matches = list(self.patterns['article'].finditer(text))
        
        for i, article_match in enumerate(article_matches):
            article_num = article_match.group(1)
            article_title = article_match.group(2).strip()
            
            # Determine end of this article
            start_pos = article_match.start()
            if i + 1 < len(article_matches):
                end_pos = article_matches[i + 1].start()
            else:
                end_pos = len(text)
            
            article_text = text[start_pos:end_pos]
            
            # Check if article has clauses
            clause_matches = list(self.patterns['clause'].finditer(article_text))
            
            if clause_matches:
                # First add the article itself as a block
                sections.append(('article', article_text, {
                    'article_num': article_num,
                    'article_title': article_title
                }))
                
                # Split by clauses
                for j, clause_match in enumerate(clause_matches):
                    clause_num = clause_match.group(1)
                    clause_title = clause_match.group(2).strip()
                    
                    # Determine clause boundaries
                    clause_start = clause_match.start()
                    if j + 1 < len(clause_matches):
                        clause_end = clause_matches[j + 1].start()
                    else:
                        # Look for next article or end
                        next_article = re.search(r'^\s*Điều\s+\d+', article_text[clause_start:], re.MULTILINE | re.IGNORECASE)
                        clause_end = next_article.start() if next_article else len(article_text)
                    
                    clause_content = article_text[clause_start:clause_start + clause_end]
                    
                    # Check for "Quy trình" pattern within clause - NEW ENHANCEMENT
                    quy_trinh_sections = self._split_by_quy_trinh_pattern(clause_content)
                    if quy_trinh_sections:
                        # Add each "Quy trình" section as separate blocks
                        for quy_trinh_section in quy_trinh_sections:
                            sections.append(('quy_trinh_clause', quy_trinh_section['content'], {
                                'article_num': article_num,
                                'article_title': article_title,
                                'clause_num': clause_num,
                                'clause_title': clause_title,
                                'quy_trinh_source': quy_trinh_section['source']
                            }))
                    else:
                        # Check for "như sau:" pattern within clause - NEW ENHANCEMENT
                        nhu_sau_sections = self._split_by_nhu_sau_pattern(clause_content)
                        if nhu_sau_sections:
                            # Add each "như sau:" section as separate blocks
                            for nhu_sau_section in nhu_sau_sections:
                                sections.append(('nhu_sau_clause', nhu_sau_section['content'], {
                                    'article_num': article_num,
                                    'article_title': article_title,
                                    'clause_num': clause_num,
                                    'clause_title': clause_title,
                                    'nhu_sau_source': nhu_sau_section['source']
                                }))
                        else:
                            # Check for numbered clauses (1., 2., 3., etc.) within clause - NEW ENHANCEMENT
                            khoan_number_sections = self._split_by_khoan_number_pattern(clause_content, article_num)
                            if khoan_number_sections:
                                # Add each numbered clause section as separate blocks
                                for khoan_section in khoan_number_sections:
                                    sections.append(('khoan_number_clause', khoan_section['content'], {
                                        'article_num': article_num,
                                        'article_title': article_title,
                                        'clause_num': clause_num,
                                        'clause_title': clause_title,
                                        'khoan_number_source': khoan_section['source']
                                    }))
                            else:
                                # Check for points within clause
                                point_matches = list(self.patterns['point_a'].finditer(clause_content)) + \
                                               list(self.patterns['point_b'].finditer(clause_content))
                                
                                if point_matches:
                                    # Split by points
                                    for k, point_match in enumerate(point_matches):
                                        point_letter = point_match.group(1)
                                        
                                        point_start = point_match.start()
                                        if k + 1 < len(point_matches):
                                            point_end = point_matches[k + 1].start()
                                        else:
                                            point_end = len(clause_content)
                                        
                                        point_content = clause_content[point_start:point_end]
                                        
                                        sections.append(('point', point_content, {
                                            'article_num': article_num,
                                            'article_title': article_title,
                                            'clause_num': clause_num,
                                            'clause_title': clause_title,
                                            'point_letter': point_letter
                                        }))
                                else:
                                    # No points, add clause as block
                                    sections.append(('clause', clause_content, {
                                        'article_num': article_num,
                                        'article_title': article_title,
                                        'clause_num': clause_num,
                                        'clause_title': clause_title
                                    }))
            else:
                # No clauses, check for "Quy trình" pattern in article first
                quy_trinh_sections = self._split_by_quy_trinh_pattern(article_text)
                if quy_trinh_sections:
                    # Add each "Quy trình" section as separate blocks
                    for quy_trinh_section in quy_trinh_sections:
                        sections.append(('quy_trinh_article', quy_trinh_section['content'], {
                            'article_num': article_num,
                            'article_title': article_title,
                            'quy_trinh_source': quy_trinh_section['source']
                        }))
                else:
                    # Check for "như sau:" pattern in article
                    nhu_sau_sections = self._split_by_nhu_sau_pattern(article_text)
                    if nhu_sau_sections:
                        # Add each "như sau:" section as separate blocks
                        for nhu_sau_section in nhu_sau_sections:
                            sections.append(('nhu_sau_article', nhu_sau_section['content'], {
                                'article_num': article_num,
                                'article_title': article_title,
                                'nhu_sau_source': nhu_sau_section['source']
                            }))
                    else:
                        # No special patterns, add article as block
                        sections.append(('article', article_text, {
                            'article_num': article_num,
                            'article_title': article_title
                        }))
        
        return sections
    
    def _split_by_nhu_sau_pattern(self, text: str) -> List[Dict[str, str]]:
        """
        Split text by "như sau:" pattern.
        
        This method handles the special Vietnamese legal pattern where:
        - Part before "như sau:" = source (title/regulation statement)
        - Part after "như sau:" = content (implementation details)
        
        Args:
            text: Text to split
            
        Returns:
            List of dictionaries with 'source' and 'content' keys
        """
        sections = []
        
        # First try to match pattern with content on same line
        nhu_sau_matches = list(self.patterns['nhu_sau_pattern'].finditer(text))
        
        if nhu_sau_matches:
            for match in nhu_sau_matches:
                source_part = match.group(1).strip()
                nhu_sau_text = match.group(2).strip()
                content_part = match.group(3).strip()
                
                # Combine "như sau:" with content
                full_content = f"{nhu_sau_text}: {content_part}"
                
                sections.append({
                    'source': source_part,
                    'content': full_content
                })
        else:
            # Try to match pattern without content on same line
            nhu_sau_simple_matches = list(self.patterns['nhu_sau_simple'].finditer(text))
            
            if nhu_sau_simple_matches:
                for match in nhu_sau_simple_matches:
                    source_part = match.group(1).strip()
                    nhu_sau_text = match.group(2).strip()
                    
                    # Find content after this line
                    match_end = match.end()
                    remaining_text = text[match_end:].strip()
                    
                    # Extract content until next legal boundary
                    content_lines = []
                    lines = remaining_text.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Stop at next legal boundary
                        if (re.search(r'^\s*Điều\s+\d+', line, re.IGNORECASE) or
                            re.search(r'^\s*Khoản\s+\d+', line, re.IGNORECASE) or
                            re.search(r'^\s*[a-zA-Z]\)\s+', line) or
                            re.search(r'^\s*Điểm\s+[a-zA-Z]', line, re.IGNORECASE)):
                            break
                        
                        content_lines.append(line)
                    
                    if content_lines:
                        full_content = f"{nhu_sau_text}: " + '\n'.join(content_lines)
                        sections.append({
                            'source': source_part,
                            'content': full_content
                        })
        
        return sections
    
    def _split_by_quy_trinh_pattern(self, text: str) -> List[Dict[str, str]]:
        """
        Split text by "Quy trình" + "Bước n:" pattern.
        
        This method handles the special Vietnamese administrative pattern where:
        - Part with "Quy trình" = source (procedure title)
        - Part with "Bước 1:", "Bước 2:", etc. = content (procedure steps)
        
        Args:
            text: Text to split
            
        Returns:
            List of dictionaries with 'source' and 'content' keys
        """
        sections = []
        
        # Find all "Quy trình" matches
        quy_trinh_matches = list(self.patterns['quy_trinh_pattern'].finditer(text))
        
        for match in quy_trinh_matches:
            # Find the start position of this quy trình
            start_pos = match.start()
            
            # Look for "Bước" patterns after this quy trình
            remaining_text = text[start_pos:]
            buoc_matches = list(self.patterns['buoc_pattern'].finditer(remaining_text))
            
            if buoc_matches:
                # Find the first "Bước" to determine where content starts
                first_buoc_pos = buoc_matches[0].start()
                
                # Extract the quy trình line (source)
                quy_trinh_end = start_pos + first_buoc_pos
                source_text = text[start_pos:quy_trinh_end].strip()
                
                # Extract content starting from first "Bước"
                content_start = start_pos + first_buoc_pos
                
                # Find where this quy trình section ends
                # Look for next legal boundary or end of text
                content_end = len(text)
                
                # Check for next legal boundaries
                next_boundaries = []
                
                # Look for next Điều
                next_dieu = re.search(r'^\s*Điều\s+\d+', text[content_start:], re.MULTILINE | re.IGNORECASE)
                if next_dieu:
                    next_boundaries.append(content_start + next_dieu.start())
                
                # Look for next Khoản
                next_khoan = re.search(r'^\s*Khoản\s+\d+', text[content_start:], re.MULTILINE | re.IGNORECASE)
                if next_khoan:
                    next_boundaries.append(content_start + next_khoan.start())
                
                # Look for next Điểm
                next_diem = re.search(r'^\s*Điểm\s+[a-zA-Z]', text[content_start:], re.MULTILINE | re.IGNORECASE)
                if next_diem:
                    next_boundaries.append(content_start + next_diem.start())
                
                # Look for footer
                next_footer = re.search(r'^(Nơi nhận|KT\.\s*HIỆU TRƯỞNG|HIỆU TRƯỞNG)', text[content_start:], re.MULTILINE | re.IGNORECASE)
                if next_footer:
                    next_boundaries.append(content_start + next_footer.start())
                
                # Use the earliest boundary
                if next_boundaries:
                    content_end = min(next_boundaries)
                
                content_text = text[content_start:content_end].strip()
                
                if content_text:
                    sections.append({
                        'source': source_text,
                        'content': content_text
                    })
        
        return sections
    
    def _split_by_chuong_pattern(self, text: str) -> List[Dict[str, str]]:
        """
        Split text by "Chương" + "Tiêu đề chương" pattern.
        
        This method handles the special Vietnamese legal structure where:
        - Part with "Chương I", "Chương II", etc. = source (chapter title)
        - Part with chapter title (e.g., "TUYỂN SINH") = additional context
        - Content = the chapter header content (usually not embedded)
        
        Args:
            text: Text to split
            
        Returns:
            List of dictionaries with 'source' and 'content' keys
        """
        sections = []
        
        # Find all "Chương" matches
        chuong_matches = list(self.patterns['chuong_pattern'].finditer(text))
        
        for match in chuong_matches:
            chuong_line = match.group(0).strip()
            
            # Find the start position of this chương
            start_pos = match.start()
            
            # Look for the next line to see if it's a chapter title
            lines = text[start_pos:].split('\n')
            if len(lines) >= 2:
                chuong_line = lines[0].strip()
                next_line = lines[1].strip()
                
                # Check if next line is a chapter title (all caps, not starting with Điều/Khoản)
                if (next_line.isupper() and 
                    not next_line.startswith('Điều') and 
                    not next_line.startswith('Khoản') and
                    len(next_line) > 3):
                    # Combine chapter number and title
                    source_text = f"{chuong_line} - {next_line}"
                    content_text = f"{chuong_line}\n{next_line}"
                else:
                    source_text = chuong_line
                    content_text = chuong_line
            else:
                source_text = chuong_line
                content_text = chuong_line
            
            sections.append({
                'source': source_text,
                'content': content_text
            })
        
        return sections
    
    def _split_by_khoan_number_pattern(self, text: str, article_num: str) -> List[Dict[str, str]]:
        """
        Split text by numbered clauses (1., 2., 3., etc.) within an article.
        
        Args:
            text: Text to split (should be within an article)
            article_num: Article number for source generation
            
        Returns:
            List of dictionaries with 'source' and 'content' keys
        """
        sections = []
        
        # Find all numbered clause matches
        khoan_matches = list(self.patterns['khoan_number_pattern'].finditer(text))
        
        for i, match in enumerate(khoan_matches):
            khoan_num = match.group(1)
            
            # Determine clause boundaries
            start_pos = match.start()
            if i + 1 < len(khoan_matches):
                end_pos = khoan_matches[i + 1].start()
            else:
                # Look for next legal boundary
                next_boundaries = []
                
                # Look for next Điều
                next_dieu = re.search(r'^\s*Điều\s+\d+', text[start_pos:], re.MULTILINE | re.IGNORECASE)
                if next_dieu:
                    next_boundaries.append(start_pos + next_dieu.start())
                
                # Look for next Chương
                next_chuong = re.search(r'^\s*Chương\s+[IVXLC\d]+', text[start_pos:], re.MULTILINE | re.IGNORECASE)
                if next_chuong:
                    next_boundaries.append(start_pos + next_chuong.start())
                
                # Look for footer
                next_footer = re.search(r'^(Nơi nhận|KT\.\s*HIỆU TRƯỞNG|HIỆU TRƯỞNG)', text[start_pos:], re.MULTILINE | re.IGNORECASE)
                if next_footer:
                    next_boundaries.append(start_pos + next_footer.start())
                
                end_pos = min(next_boundaries) if next_boundaries else len(text)
            
            content_text = text[start_pos:end_pos].strip()
            
            if content_text:
                sections.append({
                    'source': f"Điều {article_num} -> Khoản {khoan_num}",
                    'content': content_text
                })
        
        return sections
    
    def _extract_footer(self, text: str) -> str:
        """Extract footer section."""
        footer_match = self.patterns['footer'].search(text)
        if footer_match:
            return text[footer_match.start():]
        return ""
    
    def _create_block_metadata(self, doc_metadata: Dict[str, Any], 
                             section_type: str, section_info: Dict[str, Any], 
                             content: str) -> Dict[str, Any]:
        """Create metadata for a block following exact format from test.md."""
        # Check for explicit source first
        explicit_source = section_info.get('source')
        if explicit_source:
            source = explicit_source
        else:
            # Determine source based on section type following exact format
            source = ""
            
            if section_type == 'legal_basis':
                source = "Căn cứ"
            elif section_type == 'quyet_dinh':
                source = "Quyết định"
            elif section_type == 'article':
                article_num = section_info.get('article_num', '')
                source = f"Điều {article_num}"
            elif section_type == 'khoan':
                # Format: Điều X -> Khoản Y
                article_num = section_info.get('article_num', '')
                khoan_num = section_info.get('khoan_num', '')
                source = f"Điều {article_num} -> Khoản {khoan_num}"
            elif section_type == 'subsection':
                # subsection = numbered 1., 2., ... nhưng khác nhánh 'khoan'
                article_num = section_info.get('article_num', '')
                num = section_info.get('subsection_num', '')
                source = f"Điều {article_num} -> Khoản {num}"
            elif section_type == 'khoan_number_clause':
                # chuyển "Khoản n của Điều X" sang format thống nhất
                src = section_info.get('khoan_number_source', '')  # e.g., "Khoản 3 của Điều 8"
                m = re.search(r'Khoản\s+(\d+).*?Điều\s+(\d+)', src)
                if m:
                    khoan_num, article_num = m.group(1), m.group(2)
                    source = f"Điều {article_num} -> Khoản {khoan_num}"
                else:
                    # fallback
                    article_num = section_info.get('article_num', '')
                    khoan_num = section_info.get('khoan_num', '')
                    source = f"Điều {article_num} -> Khoản {khoan_num}"
            elif section_type == 'point':
                article_num = section_info.get('article_num', '')
                clause_num = section_info.get('clause_num', '') or section_info.get('khoan_num', '')
                point_letter = section_info.get('point_letter', '')
                # map Điểm a) thành "Mục a" theo rule
                source = f"Điều {article_num} -> Khoản {clause_num} -> Mục {point_letter}"
            elif section_type in ('nhu_sau_clause', 'nhu_sau_article'):
                # giữ Điều/Khoản nếu có, còn lại fallback Điều X
                article_num = section_info.get('article_num', '')
                clause_num = section_info.get('clause_num', '')
                source = f"Điều {article_num}" + (f" -> Khoản {clause_num}" if clause_num else "")
            elif section_type in ('quy_trinh_clause', 'quy_trinh_article'):
                article_num = section_info.get('article_num', '')
                clause_num = section_info.get('clause_num', '')
                source = f"Điều {article_num}" + (f" -> Khoản {clause_num}" if clause_num else "")
            elif section_type == 'chuong':
                # Format: Chương X — tiêu đề
                chuong_source = section_info.get('source', '')
                source = chuong_source
            elif section_type == 'phu_luc':
                # Format: Phụ lục X
                phu_luc_num = section_info.get('phu_luc_num', '')
                source = f"Phụ lục {phu_luc_num}"
        
        return {
            'doc_id': doc_metadata.get('doc_id', ''),
            'data_type': 'markdown',
            'category': section_info.get('category', 'training_and_regulations'),  # Use category from section_info if available
            'date': doc_metadata.get('date', ''),
            'source': source
        }
    
    def _generate_category_with_llm(self, metadata: Dict[str, Any], content: str) -> str:
        """
        Generate category using LLM with deterministic settings.
        
        Args:
            metadata: Block metadata
            content: Block content
            
        Returns:
            Category from fixed taxonomy
        """
        if not self.llm_enabled:
            return 'training_and_regulations'
        
        try:
            # Prepare input for LLM (metadata + first 800-1000 chars)
            input_text = self._prepare_llm_input(metadata, content)
            
            # Create prompt as specified in the user's requirements
            prompt = self._create_category_prompt(input_text)
            
            # Call Gemini API with deterministic settings
            response = self._call_gemini_api(prompt)
            
            # Parse response and validate against taxonomy
            category = self._parse_category_response(response)
            
            return category
            
        except Exception as e:
            logger.warning(f"LLM category generation failed: {e}")
            return 'training_and_regulations'
    
    def _prepare_llm_input(self, metadata: Dict[str, Any], content: str) -> str:
        """Prepare input for LLM (metadata + first 800-1000 chars)."""
        # Combine metadata and content
        metadata_text = f"doc_id: {metadata.get('doc_id', '')}\n"
        metadata_text += f"source: {metadata.get('source', '')}\n"
        metadata_text += f"date: {metadata.get('date', '')}\n"
        metadata_text += f"amend: {metadata.get('amend', '')}\n"
        
        # Limit content to first 800-1000 characters
        content_sample = content[:1000]
        
        return f"{metadata_text}\n{content_sample}"
    
    def _create_category_prompt(self, input_text: str) -> str:
        """Create prompt for category assignment as specified in user requirements."""
        return f"""You are a deterministic transformer for Vietnamese legal/administrative texts. Your job:
(1) Analyze the input document block metadata and content.
(2) Assign EXACTLY ONE category from the allowed taxonomy.
(3) Use temperature=0.0, top_p=1.0 for deterministic output.

======================
STRICT OUTPUT FORMAT
======================
Return ONLY the category name, nothing else.

======================
CATEGORY ASSIGNMENT
======================
Allowed taxonomy (MUST pick exactly one):
[training_and_regulations, academic_affairs, admissions, finance_and_tuition,
 examination, postgraduate_training, internship, student_affairs,
 human_resources, distance_learning]

Mapping hints (apply deterministically; if multiple match, pick the first matched below):
1) Mentions "tiến sĩ/thạc sĩ/đào tạo sau đại học/TS/ThS" → postgraduate_training
2) "tuyển sinh/xét tuyển/điều kiện dự tuyển" → admissions
3) "học phí/miễn giảm/thu/chi/quy định phí" → finance_and_tuition
4) "kỳ thi/thi cử/đánh giá/kiểm tra" → examination
5) "thực tập/TTTN/doanh nghiệp/internship" → internship
6) "đào tạo từ xa/e-learning/online/qua mạng" → distance_learning
7) "công tác sinh viên/khen thưởng/kỷ luật/học bổng/rèn luyện" → student_affairs
8) "tổ chức cán bộ/nhân sự/CBVC" → human_resources
9) "phòng đào tạo/chương trình học/tín chỉ/kế hoạch giảng dạy/GDTC/thể chất/quy chế" → academic_affairs
10) Else → training_and_regulations

If signals are weak, default to training_and_regulations.

======================
SPECIAL PATTERN HANDLING
======================
For blocks with "như sau:" pattern:
- The source field contains the regulation title/statement (before "như sau:")
- The content field contains the implementation details (after "như sau:")
- Focus on the content part for category assignment as it contains the actual rules/procedures

For blocks with "Quy trình" + "Bước n:" pattern:
- The source field contains the procedure title (the "Quy trình..." line)
- The content field contains all the steps ("Bước 1:", "Bước 2:", etc.)
- This is treated as a single block, not split into individual steps
- Category assignment should focus on the procedure context (academic_affairs for enrollment procedures, etc.)

For blocks with "Chương" + "Tiêu đề chương" pattern:
- The source field contains the chapter number and title (e.g., "Chương I - TUYỂN SINH")
- The content field contains the chapter header content (usually not embedded)
- Category assignment should prioritize chapter context (admissions for "TUYỂN SINH", academic_affairs for "ĐÀO TẠO", etc.)

For blocks with numbered clauses (1., 2., 3., etc.):
- The source field contains "Khoản n của Điều X"
- The content field contains the specific clause content
- These provide granular detail for RAG queries

======================
INPUT
======================
{input_text}

======================
OUTPUT
======================
Return ONLY the category name:"""
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API with deterministic settings."""
        if not self.llm_enabled or self.llm_service is None:
            raise Exception("Gemini API not available")
            
        try:
            return self.llm_service.call_gemini(prompt)
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    def _parse_category_response(self, response: str) -> str:
        """Parse LLM response and validate against taxonomy."""
        # Clean response
        response = response.strip().lower()
        
        # Check if response is in taxonomy
        for category in self.category_taxonomy:
            if category.lower() in response:
                return category
        
        # Default fallback
        return 'training_and_regulations'
    
    def to_markdown(self, blocks: List[LegalBlock]) -> str:
        """
        Convert blocks to Markdown format with metadata fields including confidence.
        
        Returns:
            Markdown string with blocks separated by ---
        """
        markdown_lines = []
        
        for i, block in enumerate(blocks):
            if i > 0:
                markdown_lines.append("")
                markdown_lines.append("---")
                markdown_lines.append("")
            
            # Metadata section - 6 fields: doc_id -> data_type -> category -> date -> source -> confidence
            markdown_lines.append("## Metadata")
            markdown_lines.append(f"- **doc_id:** {block.doc_id}")
            markdown_lines.append(f"- **data_type:** {block.data_type}")
            markdown_lines.append(f"- **category:** {block.category}")
            markdown_lines.append(f"- **date:** {block.date}")
            markdown_lines.append(f"- **source:** {block.source}")
            if block.confidence > 0:
                markdown_lines.append(f"- **confidence:** {block.confidence:.2f}")
            markdown_lines.append("")
            
            # Content section - PRESERVE VERBATIM
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


if __name__ == "__main__":
    # Test with sample text following exact format from test.md
    sample_text = """
ĐẠI HỌC THÁI NGUYÊN
TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG
Số: 429/QĐ-ĐHCNTT&TT
Thái Nguyên, ngày 22 tháng 6 năm 2022
QUYẾT ĐỊNH
Về việc ban hành Quy định việc biên soạn, lựa chọn, thẩm định, duyệt và sử dụng tài liệu giảng dạy, giáo trình giáo dục đại học của Trường Đại học Công nghệ Thông tin và Truyền thông

Căn cứ Quyết định số 468/QĐ-TTg ngày 30 tháng 3 năm 2011 của Thủ tướng Chính phủ về việc thành lập Trường Đại học Công nghệ Thông tin và Truyền thông thuộc Đại học Thái Nguyên;
Căn cứ Nghị quyết số 15/NQ-HĐT ngày 24 tháng 9 năm 2021 của Chủ tịch Hội đồng trường Trường Đại học Công nghệ Thông tin và Truyền thông về việc ban hành Quy chế tổ chức và hoạt động của Trường Đại học Công nghệ Thông tin và Truyền thông thuộc Đại học Thái Nguyên;
Theo đề nghị của Trưởng phòng Đào tạo,

**Điều 1.** Ban hành kèm theo Quyết định này "Quy định việc biên soạn, lựa chọn, thẩm định, duyệt và sử dụng tài liệu giảng dạy, giáo trình giáo dục đại học của Trường Đại học Công nghệ Thông tin và Truyền thông".
**Điều 2.** Quyết định có hiệu lực kể từ ngày ký. Quyết định này thay thế Quyết định số 1271/QĐ-ĐHCNTT&TT ngày 28 tháng 11 năm 2017 về việc ban hành Quy định biên soạn, lựa chọn, thẩm định, duyệt và sử dụng tài liệu giảng dạy, giáo trình giáo dục đại học của Trường ĐH CNTT&TT.
**Điều 3.** Thủ trưởng các đơn vị, viên chức và người lao động thuộc Trường Đại học Công nghệ Thông tin và Truyền thông chịu trách nhiệm thi hành Quyết định này./.

**Chương I — QUY ĐỊNH CHUNG**

**Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng**

1. Văn bản này quy định về việc biên soạn, lựa chọn, thẩm định, duyệt, xuất bản, phát hành và sử dụng tài liệu giảng dạy, giáo trình giáo dục đại học tại Trường Đại học Công nghệ Thông tin và Truyền thông (ĐH CNTT&TT).
2. Quy định này áp dụng đối với các khoa, bộ môn, các giảng viên giảng dạy học phần trình độ đại học, sau đại học tại Trường Đại học Công nghệ Thông tin và Truyền thông. Quy định này không áp dụng đối với biên soạn, thẩm định, lựa chọn, xuất bản, phát hành, sử dụng giáo trình chung các học phần lý luận chính trị, quốc phòng - an ninh.

**Điều 2. Giải thích từ ngữ**
Tài liệu giảng dạy bắt buộc bao gồm: đề cương học phần, giáo trình, bài giảng, và tài liệu tham khảo.

1. **Đề cương học phần hay môn học**: khung chi tiết nội dung của học phần, định hướng cho hoạt động dạy và học; là cơ sở biên soạn bài giảng, xác định và lựa chọn giáo trình, tài liệu tham khảo; sử dụng thống nhất trong toàn trường, do bộ môn biên soạn, Hiệu trưởng phê duyệt.
2. **Giáo trình**: tài liệu chính của một học phần, do nhà trường tổ chức biên soạn, lựa chọn, thẩm định, phê duyệt và sử dụng theo Quy định này và pháp luật liên quan.
3. **Bài giảng**: tài liệu biên soạn để giảng dạy mỗi học phần, dựa trên đề cương học phần, giáo trình chính thức, tài liệu tham khảo.
4. **Tài liệu tham khảo**: các sách, bài báo, công trình khoa học, tài liệu đã công bố, cả điện tử; dùng để bổ sung kiến thức cho giảng viên và người học.

**Điều 8. Sử dụng giáo trình và tài liệu để giảng dạy**

1. Đối với các giáo trình nhà trường đã xuất bản, Trường Đại học CNTT&TT được cung cấp, phát, tặng, cho, cho thuê, trao đổi, cho mượn, làm tài liệu dùng chung, cung cấp cho nguồn tài nguyên giáo dục mở để đưa xuất bản phẩm đến với người sử dụng bảo đảm tuân thủ các quy định của pháp luật có liên quan.

2. Giáo trình đã được phê duyệt của nhà trường phải được sử dụng là tài liệu chính; một giáo trình có thể dùng cho nhiều học phần phù hợp.

3. Trình độ đại học: mỗi học phần có ít nhất một giáo trình là tài liệu chính; nội dung giáo trình đáp ứng tối thiểu **70%**nội dung kiến thức của học phần.

4. Trình độ thạc sĩ: phải có giáo trình là tài liệu chính; nếu chưa có, dùng tài liệu thay thế đáp ứng tối thiểu **70%**nội dung kiến thức.

5. Trình độ tiến sĩ: bảo đảm có giáo trình hoặc tài liệu để giảng dạy, học tập và nghiên cứu; có tài liệu chuyên khảo, công trình khoa học liên quan, phù hợp mục tiêu và chương trình đào tạo.

6. Trước khi đưa vào sử dụng, giáo trình phải được biên soạn/lựa chọn/thẩm định/phê duyệt theo Quy định và pháp luật liên quan; tài liệu thay thế giáo trình phải được phê duyệt theo quy định của nhà trường.

7. Nhà trường công khai các giáo trình, tài liệu cho từng nội dung, chuyên đề, học phần và xếp hạng theo thứ tự ưu tiên.

8. Hằng năm, lấy ý kiến giảng viên và người học để cập nhật, điều chỉnh giáo trình cho phù hợp.

**Điều 9. Sử dụng bài giảng và tài liệu tham khảo**

1. Bài giảng trước khi sử dụng phải được thẩm định và phê duyệt.

2. Bài giảng phải được cung cấp cho người học trước, trong hoặc sau giờ giảng.

3. Tài liệu tham khảo phải được công khai thông tin, thường xuyên bổ sung; bảo đảm khả năng truy cập, sử dụng.

**Phụ lục 1 — QUY CÁCH TRÌNH BÀY CỦA BÀI GIẢNG**

**1. Soạn thảo văn bản, khổ giấy, định dạng, font, size**

*Soạn trên MS Word hoặc tương đương; khổ A4; căn lề: trên 2,5 cm, dưới 2,5 cm, trái 3 cm, phải 2 cm; Unicode; Times New Roman; giãn dòng nội dung **1,2 lines**.

**2. Tên bài giảng (trang bìa)**

*Viết ngắn gọn, rõ nội dung; không viết tắt; căn giữa; in **CHỮ HOA, cỡ 20**.

**3. Bố cục của bài giảng**

*Trang bìa; trang phụ bìa; mục lục; danh mục từ viết tắt; bộ thuật ngữ; các chương và bài kèm mục tiêu; câu hỏi củng cố và bài tập; danh mục tài liệu tham khảo; phụ lục; FAQ; phần bài tập thực hành theo từng chương với mục đích, yêu cầu, bài mẫu, bài cơ bản, nâng cao; đặt tên bài tập dạng **Bài x.y**; tổng nội dung **≤ 200 trang A4**, lý thuyết **≤ 150 trang A4**.
"""
    
    result = split_vietnamese_legal_document(sample_text)
    
    # Write to file to avoid encoding issues
    with open('test_output.md', 'w', encoding='utf-8') as f:
        f.write(result)
    
    print("Test completed! Output written to test_output.md")
