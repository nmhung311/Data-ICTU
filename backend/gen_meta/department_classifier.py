#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Department Classifier: Phân loại department từ nội dung văn bản pháp lý Việt Nam.
Sử dụng rule-based matching từ khóa -> department.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Bộ mapping từ khóa -> department (theo thứ tự ưu tiên từ cao xuống thấp)
DEPARTMENT_KEYWORDS = {
    'Training Department': ['đào tạo', 'giảng dạy', 'giáo trình', 'học tập', 'sinh viên'],
    'Academic Affairs': ['học vụ', 'đăng ký', 'tín chỉ', 'kết quả học tập'],
    'Student Affairs': ['sinh viên', 'học sinh', 'quản lý sinh viên'],
    'Finance': ['tài chính', 'học phí', 'ngân sách'],
    'Administration': ['hành chính', 'quản lý', 'tổ chức']
}

DEFAULT_DEPARTMENT = 'Training Department'


def extract_department_from_content(text: str) -> str:
    """
    Phân loại department từ nội dung văn bản sử dụng rule-based matching.
    
    Args:
        text: Nội dung văn bản cần phân loại
        
    Returns:
        Department string
    """
    if not text or not isinstance(text, str):
        return DEFAULT_DEPARTMENT
    
    text_lower = text.lower()
    
    # Tìm department khớp đầu tiên (theo thứ tự ưu tiên)
    for department, keywords in DEPARTMENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                logger.debug(f"Content matched department '{department}' (keyword: '{keyword}')")
                return department
    
    # Không tìm thấy khớp, trả về mặc định
    logger.debug(f"Content -> department '{DEFAULT_DEPARTMENT}' (no match)")
    return DEFAULT_DEPARTMENT


def get_available_departments() -> list:
    """Lấy danh sách tất cả department có sẵn."""
    return list(DEPARTMENT_KEYWORDS.keys())


def get_department_keywords() -> Dict[str, list]:
    """Lấy dictionary mapping department -> keywords."""
    return DEPARTMENT_KEYWORDS.copy()


def update_department_keywords(department: str, keywords: list) -> bool:
    """
    Cập nhật keywords cho một department cụ thể.
    
    Args:
        department: Tên department cần cập nhật
        keywords: Danh sách keywords mới
        
    Returns:
        True nếu cập nhật thành công, False nếu department không tồn tại
    """
    if department not in DEPARTMENT_KEYWORDS:
        logger.warning(f"Department '{department}' không tồn tại")
        return False
    
    DEPARTMENT_KEYWORDS[department] = keywords
    logger.info(f"Đã cập nhật keywords cho department '{department}'")
    return True


def add_department(department: str, keywords: list) -> bool:
    """
    Thêm department mới.
    
    Args:
        department: Tên department mới
        keywords: Danh sách keywords
        
    Returns:
        True nếu thêm thành công, False nếu department đã tồn tại
    """
    if department in DEPARTMENT_KEYWORDS:
        logger.warning(f"Department '{department}' đã tồn tại")
        return False
    
    DEPARTMENT_KEYWORDS[department] = keywords
    logger.info(f"Đã thêm department mới '{department}'")
    return True


def set_default_department(department: str) -> bool:
    """
    Thay đổi department mặc định.
    
    Args:
        department: Tên department mới dùng làm mặc định
        
    Returns:
        True nếu thành công, False nếu department không tồn tại
    """
    global DEFAULT_DEPARTMENT
    
    if department not in DEPARTMENT_KEYWORDS and department != DEFAULT_DEPARTMENT:
        logger.warning(f"Department '{department}' không tồn tại")
        return False
    
    DEFAULT_DEPARTMENT = department
    logger.info(f"Đã thay đổi department mặc định thành '{department}'")
    return True

