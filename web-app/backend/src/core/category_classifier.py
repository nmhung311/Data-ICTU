#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Category Classifier: Phân loại category từ tên file văn bản pháp lý Việt Nam.
Sử dụng rule-based matching từ khóa -> category.
"""

import os
import logging
from typing import List
from collections import OrderedDict

logger = logging.getLogger(__name__)

# Bộ mapping từ khóa -> category (theo thứ tự ưu tiên từ cao xuống thấp)
KEYWORD_MAPPING = OrderedDict({
    "admissions": ["tuyển sinh", "xét tuyển", "dự tuyển"],
    "postgraduate_training": ["thạc sĩ", "tiến sĩ", "sau đại học", "thạc sỹ", "tiến sỹ"],
    "academic_affairs": ["đào tạo", "tín chỉ", "ctđt", "gdtc", "giảng dạy", "học tập", "giáo trình", "chuẩn đầu ra", "tin học", "ngoại ngữ", "chương trình", "khung chương trình"],
    "internship": ["thực tập", "tttn", "đồ án", "khóa luận", "khoá luận"],
    "distance_learning": ["đào tạo từ xa", "e-learning", "trực tuyến", "online"],
    "finance_and_tuition": ["học phí", "tài chính", "miễn", "giảm", "phí"],
    "examination": ["thi cử", "kiểm tra", "đánh giá", "kỳ thi", "kết quả học tập"],
    "human_resources": ["cán bộ", "giảng viên", "cbvc", "nhân sự", "tuyển dụng"],
    "student_affairs": ["công tác sinh viên", "ngoại khóa", "hoạt động", "học bổng", "khen thưởng", "kỷ luật"],
    "training_and_regulations": ["quy chế", "quy định", "nội quy", "quy tắc"]  # mặc định cuối cùng
})

DEFAULT_CATEGORY = "training_and_regulations"
SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md']


def normalize_filename(filename: str) -> str:
    """
    Chuẩn hóa tên file: chuyển về lowercase, bỏ đuôi file.
    
    Args:
        filename: Tên file gốc
        
    Returns:
        Tên file đã chuẩn hóa
    """
    # Lấy tên file không có đường dẫn
    basename = os.path.basename(filename)
    
    # Bỏ đuôi file
    name_without_ext = basename
    for ext in SUPPORTED_EXTENSIONS:
        if basename.lower().endswith(ext.lower()):
            name_without_ext = basename[:-len(ext)]
            break
    
    # Chuyển về lowercase và loại bỏ khoảng trắng thừa
    normalized = name_without_ext.lower().strip()
    
    return normalized


def classify_by_filename(filename: str) -> str:
    """
    Phân loại category từ tên file sử dụng rule-based matching.
    
    Args:
        filename: Tên file cần phân loại
        
    Returns:
        Category string
    """
    if not filename or not isinstance(filename, str):
        return DEFAULT_CATEGORY
    
    # Chuẩn hóa tên file
    normalized = normalize_filename(filename)
    
    # Tìm category khớp đầu tiên (theo thứ tự ưu tiên)
    for category, keywords in KEYWORD_MAPPING.items():
        for keyword in keywords:
            if keyword in normalized:
                logger.debug(f"File '{filename}' -> category '{category}' (keyword: '{keyword}')")
                return category
    
    # Không tìm thấy khớp, trả về mặc định
    logger.debug(f"File '{filename}' -> category '{DEFAULT_CATEGORY}' (no match)")
    return DEFAULT_CATEGORY


def get_available_categories() -> List[str]:
    """Lấy danh sách tất cả category có sẵn."""
    return list(KEYWORD_MAPPING.keys())


def classify_by_content(content: str) -> str:
    """
    Phân loại category từ nội dung văn bản sử dụng rule-based matching.
    
    Args:
        content: Nội dung văn bản cần phân loại
        
    Returns:
        Category string
    """
    if not content or not isinstance(content, str):
        return DEFAULT_CATEGORY
    
    content_lower = content.lower()
    
    # Mapping từ khóa -> category (theo thứ tự ưu tiên)
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
                logger.debug(f"Content analysis: '{keyword}' -> '{category}'")
                return category
    
    # Default
    return DEFAULT_CATEGORY
