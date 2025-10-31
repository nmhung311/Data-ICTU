#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module riêng xử lý block Căn cứ
Tách ra để dễ sửa chữa và bảo trì
"""

import re
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


# NOTE: extract_can_cu_block() đã bị thay thế bởi create_can_cu_blocks()
# Giữ lại để backward compatibility nếu có code cũ đang dùng
def extract_can_cu_block(text: str) -> str:
    """
    [DEPRECATED] Lấy block Căn cứ (tổng quát cho mọi văn bản).
    Hàm này đã bị thay thế bởi create_can_cu_blocks().
    Giữ lại để backward compatibility.
    """
    blocks = create_can_cu_blocks(text)
    if blocks:
        # Trả về content của block đầu tiên
        return blocks[0][1] if len(blocks[0]) > 1 else ""
    return ""


def create_can_cu_blocks(text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
    """
    Tạo block 'Căn cứ' độc lập và riêng biệt.
    Hàm này HOÀN TOÀN TÁCH BIỆT với các hàm parse khác.
    Sử dụng logic để tìm các dòng "Căn cứ" và "Theo".
    
    Returns:
        List of tuples: (section_type, content, section_info)
    """
    sections = []
    
    # Sử dụng logic từ split_doc.py
    lines = text.splitlines()
    legal_basis_lines = []
    in_basis_block = False
    
    # Duyệt các dòng để tìm các block "Căn cứ"/"Theo ..."
    for line in lines:
        striped = line.strip()
        
        # Dừng nếu gặp "QUYẾT ĐỊNH" hoặc "Quyết định" (bỏ qua ký tự markdown *, #, **)
        if re.search(r"(QUYẾT[\s]*ĐỊNH|Quyết[\s]*định)\s*:", striped, re.IGNORECASE):
            break
        
        # Dấu hiệu bắt đầu căn cứ (tìm "Căn cứ" hoặc "Theo" bất kỳ đâu trong dòng, bao gồm có dấu *)
        if re.search(r"Căn\s*cứ|Theo\s+đề\s+nghị", striped, re.IGNORECASE):
            legal_basis_lines.append(line.rstrip())  # Giữ nguyên với strip newline
            in_basis_block = True
        # Sau khi đã vào block căn cứ, lấy TẤT CẢ dòng (kể cả trống) cho đến "QUYẾT ĐỊNH"
        elif in_basis_block:
            legal_basis_lines.append(line.rstrip())  # Giữ nguyên format
        else:
            # Nếu chưa vào block căn cứ thì bỏ qua
            continue
    
    can_cu_content = "\n".join(legal_basis_lines).strip()
    
    # Xóa tất cả ký tự * trong nội dung
    if can_cu_content:
        can_cu_content = can_cu_content.replace('*', '')
    
    if can_cu_content and can_cu_content.strip():
        logger.info(f"Căn cứ block: {len(can_cu_content)} chars")
        section_info = {
            'name': 'Căn cứ',
            'source': 'Căn cứ',
            'category': 'source_doc'
        }
        sections.append(('legal_basis', can_cu_content, section_info))
    
    return sections


def _fold_text(s: str) -> str:
    """
    Chuẩn hóa so khớp: hạ chữ thường, bỏ dấu tiếng Việt, nén whitespace.
    Dùng để TÌM VỊ TRÍ, sau đó cắt từ bản gốc để giữ nguyên văn.
    """
    import unicodedata
    
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
    import unicodedata
    
    # Xây map tích lũy
    o, f = 0, 0
    while o < len(original) and f < idx_in_folded:
        # tiến từng ký tự folded bằng cách bỏ dấu/normalize của original[o]
        ch = original[o]
        ch_fold = _fold_text(ch)
        if ch_fold:
            f += len(ch_fold)
        else:
            # ký tự chỉ dấu, không đóng góp
            pass
        o += 1
    return o


def build_can_cu_markdown(metadata: Dict[str, str], keyword: str, content_body: str = None) -> str:
    """
    Tạo block markdown 'Căn cứ' theo mẫu yêu cầu.
    
    Args:
        metadata: Dict chứa doc_id, department, type_data, category, date
        keyword: Từ khóa để chèn vào tiêu đề
        content_body: Optional. Nội dung căn cứ (nếu None thì chỉ có tiêu đề)
    
    Returns:
        Chuỗi markdown đầy đủ với metadata header và nội dung
    """
    doc_id = metadata.get('doc_id', '')
    department = metadata.get('department', '')
    type_data = metadata.get('type_data', 'markdown')
    category = metadata.get('category', '')
    date = metadata.get('date', '')
    source = 'Căn cứ'

    header = (
        f"## Metadata\n"
        f"- **doc_id:** {doc_id}\n"
        f"- **department:** {department}\n"
        f"- **type_data:** {type_data}\n"
        f"- **category:** {category}\n"
        f"- **date:** {date}\n"
        f"- **source:** {source}\n\n"
    )

    # Luôn có title line, ngay cả khi keyword rỗng
    if keyword and keyword.strip():
        title_line = f"Các căn cứ pháp lý để ban hành quy định liên quan đến {keyword}\n\n"
    else:
        title_line = "Các căn cứ pháp lý để ban hành quy định\n\n"
    
    body = "## Nội dung\n\n" + title_line
    
    if content_body:
        body += content_body.strip() + ("\n" if not content_body.endswith("\n") else "")
    
    return header + body


# Alias để backward compatibility
def build_can_cu_markdown_with_content(metadata: Dict[str, str], keyword: str, content_body: str) -> str:
    """
    [DEPRECATED] Alias cho build_can_cu_markdown() với content_body.
    Sử dụng build_can_cu_markdown() thay thế.
    """
    return build_can_cu_markdown(metadata, keyword, content_body)