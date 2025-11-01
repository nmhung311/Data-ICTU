#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module riêng xử lý block Quyết định
Tách ra để dễ sửa chữa và bảo trì
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
import unicodedata

logger = logging.getLogger(__name__)


def _fold_text(s: str) -> str:
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


def extract_quyet_dinh_block(text: str) -> str:
    """
    Lấy block Quyết định (tổng quát):
      - Phạm vi: từ 'QUYẾT ĐỊNH:' → trước 'Nơi nhận:' hoặc hết văn bản
      - Xóa ký tự markdown (*, #, **) ở đầu các dòng
    """
    # Tìm "QUYẾT ĐỊNH:" trong text - BỎ QUA heading markdown "## QUYẾT ĐỊNH"
    # Chỉ lấy phần "**QUYẾT ĐỊNH:**" hoặc "QUYẾT ĐỊNH:"
    p_noi_nhan = re.compile(r"Nơi\s+nhận\s*:", re.IGNORECASE)
    
    # Try pattern 1: "**QUYẾT ĐỊNH:**" (bold với **)
    m_start = re.search(r"\*\*QUYẾT\s*ĐỊNH\s*:", text, re.IGNORECASE)
    
    # Try pattern 2: "QUYẾT ĐỊNH:" (plain text, không có markdown)
    if not m_start:
        m_start = re.search(r"(?<!##\s)(?<!\*\*)QUYẾT\s*ĐỊNH\s*:", text, re.IGNORECASE)
    
    if not m_start:
        return ""
    
    start_idx = m_start.start()
    
    # Tìm "Nơi nhận:" sau "QUYẾT ĐỊNH"
    m_noi = p_noi_nhan.search(text, pos=start_idx)
    if m_noi:
        end_idx = m_noi.start()
    else:
        end_idx = len(text)
    
    block = text[start_idx:end_idx]
    
    # Xóa tất cả ký tự markdown (*, **, #) trong toàn bộ block
    block = block.replace('**', '').replace('*', '')
    # Xóa # từ đầu các dòng
    block = re.sub(r'^#+\s*', '', block, flags=re.MULTILINE)
    
    return block.strip()


def find_quyet_dinh_span(text: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Trả về (qd_start_char, qd_end_char_exclusive, qd_start_line, qd_end_line)
    - qd_end_line là dòng TRƯỚC 'Nơi nhận' (nếu có), còn nếu không có thì tới hết văn bản.
    """
    # Cho phép #, **, có/không dấu : và có text cùng dòng
    qd_pat = re.compile(
        r'(?im)^[ \t]*#*\s*\*{0,2}\s*(QUYẾT\s*ĐỊNH|Quyết\s*định)\*{0,2}\s*:?[^\n]*$'
    )
    # "Nơi nhận": linh hoạt, có/không dấu :
    noi_nhan_pat = re.compile(r'(?im)^[ \t]*[\*\-\u2022]?\s*N[ơo]i\s+nh[aă]n\s*:?')

    m_qd = qd_pat.search(text)
    if not m_qd:
        return None, None, None, None

    qd_start_char = m_qd.start()

    # 1) Ưu tiên tìm "Nơi nhận"
    m_noi_nhan = noi_nhan_pat.search(text, m_qd.end())
    if m_noi_nhan:
        qd_end_char = m_noi_nhan.start()
    else:
        # 2) Fallback: tìm chữ ký hoặc ranh giới pháp lý đầu tiên sau QĐ
        end_candidates = []

        # Chữ ký, đóng dấu phổ biến
        signature_pat = re.compile(r'(?im)^(KT\.\s*HIỆU TRƯỞNG|HIỆU TRƯỞNG|TM\.\s*|GIÁM ĐỐC|CHỦ TỊCH)\b')
        m_sig = signature_pat.search(text, m_qd.end())
        if m_sig:
            end_candidates.append(m_sig.start())

        # Ranh giới pháp lý: Điều/Chương/Phụ lục đầu tiên SAU dòng QĐ
        article_pat = re.compile(r'(?im)^[ \t]*\*{0,2}\s*Điều\s+\d+')
        chuong_pat  = re.compile(r'(?im)^[ \t]*\*{0,2}\s*Chương\s+[IVXLC\d]+')
        phuluc_pat  = re.compile(r'(?im)^[ \t]*\*{0,2}\s*Phụ\s*lục\s+\d+')

        for p in (article_pat, chuong_pat, phuluc_pat):
            m = p.search(text, m_qd.end())
            if m:
                end_candidates.append(m.start())

        # Nếu có ứng viên thì chốt trước mốc nhỏ nhất, nếu không thì hết file
        qd_end_char = min(end_candidates) if end_candidates else len(text)

    # Map char -> line
    prefix = text[:qd_start_char]
    qd_start_line = prefix.count('\n')

    # end_line là dòng TRƯỚC mốc kết thúc
    qd_end_line = text[:qd_end_char].count('\n') - 1
    if qd_end_line < qd_start_line:
        qd_end_line = qd_start_line  # phòng rìa

    logger.info(f"[QD-SPAN] qd_start_line={qd_start_line} qd_end_line={qd_end_line}")
    return qd_start_char, qd_end_char, qd_start_line, qd_end_line


def extract_quyet_dinh_to_noi_nhan(lines: List[str], start_pos: int) -> Tuple[str, int]:
    """
    Trích đoạn từ dòng 'Quyết định' đến TRƯỚC 'Nơi nhận'.
    Không dừng ở Điều/Chương/Phụ lục. Chỉ dừng khi gặp 'Nơi nhận' (mọi biến thể) hoặc hết tài liệu.
    Trả về (content, end_index) với end_index là chỉ số dòng CUỐI CÙNG đã đưa vào block Quyết định.
    """
    buf: List[str] = []
    i = start_pos

    # Thêm chính dòng 'Quyết định'
    buf.append(lines[i])
    i += 1

    # Nhận diện 'Nơi nhận' (chịu *, -, bullet •, có/không dấu, cho phép nội dung sau :)
    noi_nhan_pat = re.compile(r'(?mi)^\s*[\*\-\u2022]?\s*N[ơo]i\s+nh[aă]n\s*:[^\n]*$')

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()

        # Nếu gặp 'Nơi nhận' thì dừng TRƯỚC dòng đó (không append dòng này)
        if noi_nhan_pat.search(line):
            break

        # Không dừng ở Điều/Chương/Phụ lục. Yêu cầu là GOM HẾT trong block Quyết định.
        buf.append(raw_line)
        i += 1

    # end_pos là dòng cuối cùng đã append vào buf
    end_pos = (i - 1) if buf else start_pos
    content = '\n'.join(buf).rstrip()
    return content, end_pos


def extract_quyet_dinh_section(text: str, legal_basis_pattern) -> str:
    """
    Extract section from QUYẾT ĐỊNH to Điều 1 (excluding Căn cứ).
    
    Args:
        text: Full text to search
        legal_basis_pattern: Regex pattern for legal basis from EnhancedVnLegalSplitter
    """
    lines = text.split('\n')
    quyet_dinh_lines = []
    in_quyet_dinh = False
    
    for line in lines:
        if re.search(r'^\s*QUYẾT\s*ĐỊNH', line, re.IGNORECASE):
            in_quyet_dinh = True
            quyet_dinh_lines.append(line)
        elif in_quyet_dinh:
            # Stop at Căn cứ or first article
            if (legal_basis_pattern.search(line) or 
                re.search(r'^\s*Điều\s+\d+', line, re.IGNORECASE)):
                break
            quyet_dinh_lines.append(line)
    
    return '\n'.join(quyet_dinh_lines) if quyet_dinh_lines else ""


def build_quyet_dinh_markdown(metadata: Dict[str, str], keyword: str) -> str:
    """
    Tạo block markdown 'Quyết định' theo mẫu yêu cầu, chèn {key_word} vào phần tiêu đề nội dung.
    """
    doc_id = metadata.get('doc_id', '')
    department = metadata.get('department', '')
    type_data = metadata.get('type_data', 'markdown')
    category = metadata.get('category', '')
    date = metadata.get('date', '')
    source = 'Quyết định'

    header = (
        f"## Metadata\n"
        f"- **doc_id:** {doc_id}\n"
        f"- **department:** {department}\n"
        f"- **type_data:** {type_data}\n"
        f"- **category:** {category}\n"
        f"- **date:** {date}\n"
        f"- **source:** {source}\n\n"
    )

    body = (
        "## Nội dung\n\n"
        f"QUYẾT ĐỊNH ban hành các quy định liên quan đến {keyword}\n"
    )

    return header + body


def build_quyet_dinh_markdown_with_content(metadata: Dict[str, str], keyword: str, content_body: str) -> str:
    """
    Tạo block markdown 'Quyết định' theo mẫu, tiêu đề chứa {key_word}, sau đó nối nội dung gốc (các Điều ...).
    """
    doc_id = metadata.get('doc_id', '')
    department = metadata.get('department', '')
    type_data = metadata.get('type_data', 'markdown')
    category = metadata.get('category', '')
    date = metadata.get('date', '')
    source = 'Quyết định'

    header = (
        f"## Metadata\n"
        f"- **doc_id:** {doc_id}\n"
        f"- **department:** {department}\n"
        f"- **type_data:** {type_data}\n"
        f"- **category:** {category}\n"
        f"- **date:** {date}\n"
        f"- **source:** {source}\n\n"
    )

    title_line = f"QUYẾT ĐỊNH ban hành các quy định liên quan đến {keyword}\n\n"
    return header + "## Nội dung\n\n" + title_line + content_body.strip() + ("\n" if not content_body.endswith("\n") else "")