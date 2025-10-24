#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module phân loại category tự động từ tên file văn bản pháp lý Việt Nam.
Mục đích: Ánh xạ tên file thành category chuẩn cho hệ thống RAG mà không cần gọi LLM.

Author: AI Assistant
Date: 2024
"""

import os
import logging
from typing import List, Dict, Tuple, Any
from collections import OrderedDict

# Import LLM service
from .llm_service import get_llm_service, LLMConfig

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bộ mapping từ khóa -> category (theo thứ tự ưu tiên)
MAPPING = OrderedDict({
    "admissions": ["tuyển sinh"],
    "postgraduate_training": ["thạc sĩ", "tiến sĩ", "sau đại học"],
    "academic_affairs": ["đào tạo", "tín chỉ", "ctđt", "gdtc", "giảng dạy", "học tập", "giáo trình", "chuẩn đầu ra", "tin học", "ngoại ngữ"],
    "internship": ["thực tập", "tttn", "đồ án", "khoá luận"],
    "distance_learning": ["đào tạo từ xa", "e-learning"],
    "finance_and_tuition": ["học phí", "tài chính", "miễn", "giảm"],
    "scholarships": ["học bổng"],
    "social_policy": ["trợ cấp", "xã", "thôn", "hỗ trợ học tập", "chính sách"],
    "student_affairs": ["ngoại khóa", "đánh giá hoạt động"],
    "student_management": ["ctsv", "nội quy", "thẻ sinh viên", "ứng xử", "an ninh"],
    "certificate_management": ["văn bằng", "phôi bằng", "chứng chỉ", "quản lý bằng"],
    "student_conduct": ["rèn luyện"],
    "legal_framework": ["văn bản hợp nhất"]
})

# Category mặc định khi không khớp từ khóa nào
DEFAULT_CATEGORY = "training_and_regulations"

# Các đuôi file được hỗ trợ
SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt']


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


def find_matching_keywords(normalized_filename: str) -> List[Tuple[str, str]]:
    """
    Tìm các từ khóa khớp trong tên file và trả về danh sách (category, keyword).
    
    Args:
        normalized_filename: Tên file đã chuẩn hóa
        
    Returns:
        Danh sách các tuple (category, keyword) đã khớp
    """
    matches = []
    
    for category, keywords in MAPPING.items():
        for keyword in keywords:
            if keyword in normalized_filename:
                matches.append((category, keyword))
                logger.debug(f"Khớp từ khóa '{keyword}' -> category '{category}' trong file '{normalized_filename}'")
    
    return matches


def classify_by_filename(filename: str, use_llm: bool = False, api_key: str = None) -> Dict[str, Any]:
    """
    Phân loại category từ tên file với tùy chọn sử dụng LLM.
    
    Args:
        filename: Tên file cần phân loại
        use_llm: Có sử dụng LLM hay không (default: False)
        api_key: API key cho LLM (optional)
        
    Returns:
        Dict với category, confidence và method được sử dụng
    """
    if not filename or not isinstance(filename, str):
        logger.warning(f"Tên file không hợp lệ: {filename}")
        return {
            'category': DEFAULT_CATEGORY,
            'confidence': 0.0,
            'method': 'error',
            'reasoning': 'Tên file không hợp lệ'
        }
    
    # Sử dụng LLM nếu được yêu cầu
    if use_llm:
        try:
            llm_service = get_llm_service(api_key)
            if llm_service.is_available():
                result = llm_service.classify_category("", filename)
                logger.info(f"LLM phân loại file '{filename}' -> Category: '{result['category']}' (confidence: {result.get('confidence', 0.0)})")
                return {
                    'category': result['category'],
                    'confidence': result.get('confidence', 0.0),
                    'method': 'llm',
                    'reasoning': result.get('reasoning', 'LLM classification')
                }
            else:
                logger.warning("LLM service không có sẵn, fallback về rule-based")
        except Exception as e:
            logger.warning(f"Lỗi khi sử dụng LLM: {e}, fallback về rule-based")
    
    # Rule-based classification (fallback hoặc default)
    normalized_filename = normalize_filename(filename)
    logger.debug(f"Tên file chuẩn hóa: '{normalized_filename}'")
    
    matches = find_matching_keywords(normalized_filename)
    
    if not matches:
        logger.info(f"Không tìm thấy từ khóa khớp cho file '{filename}' -> gán category mặc định")
        return {
            'category': DEFAULT_CATEGORY,
            'confidence': 0.0,
            'method': 'rule_based',
            'reasoning': 'Không tìm thấy từ khóa khớp'
        }
    
    first_match_category = matches[0][0]
    
    if len(matches) > 1:
        matched_keywords = [match[1] for match in matches]
        logger.info(f"File '{filename}' khớp nhiều từ khóa: {matched_keywords}. Chọn category '{first_match_category}'")
    
    logger.info(f"File '{filename}' -> Category: '{first_match_category}'")
    return {
        'category': first_match_category,
        'confidence': 0.8,  # Rule-based có confidence cố định
        'method': 'rule_based',
        'reasoning': f'Khớp từ khóa: {matches[0][1]}'
    }


def bulk_classify(file_list: List[str], use_llm: bool = False, api_key: str = None) -> Dict[str, Dict[str, Any]]:
    """
    Phân loại category cho nhiều file cùng lúc với tùy chọn LLM.
    
    Args:
        file_list: Danh sách tên file
        use_llm: Có sử dụng LLM hay không (default: False)
        api_key: API key cho LLM (optional)
        
    Returns:
        Dictionary mapping filename -> classification result
    """
    if not file_list:
        logger.warning("Danh sách file trống")
        return {}
    
    results = {}
    logger.info(f"Bắt đầu phân loại {len(file_list)} file... (LLM: {use_llm})")
    
    for filename in file_list:
        try:
            result = classify_by_filename(filename, use_llm, api_key)
            results[filename] = result
        except Exception as e:
            logger.error(f"Lỗi khi phân loại file '{filename}': {e}")
            results[filename] = {
                'category': DEFAULT_CATEGORY,
                'confidence': 0.0,
                'method': 'error',
                'reasoning': f'Lỗi: {str(e)}'
            }
    
    # Thống kê kết quả
    category_counts = {}
    method_counts = {}
    for result in results.values():
        category = result['category']
        method = result['method']
        category_counts[category] = category_counts.get(category, 0) + 1
        method_counts[method] = method_counts.get(method, 0) + 1
    
    logger.info(f"Hoàn thành phân loại. Thống kê category: {category_counts}")
    logger.info(f"Thống kê method: {method_counts}")
    return results


def get_available_categories() -> List[str]:
    """
    Lấy danh sách tất cả category có sẵn.
    
    Returns:
        Danh sách category
    """
    return list(MAPPING.keys()) + [DEFAULT_CATEGORY]


def get_keywords_for_category(category: str) -> List[str]:
    """
    Lấy danh sách từ khóa của một category.
    
    Args:
        category: Tên category
        
    Returns:
        Danh sách từ khóa
    """
    return MAPPING.get(category, [])


def add_keyword_to_category(category: str, keyword: str) -> bool:
    """
    Thêm từ khóa mới vào category (chỉ trong runtime, không lưu vĩnh viễn).
    
    Args:
        category: Tên category
        keyword: Từ khóa mới
        
    Returns:
        True nếu thành công, False nếu category không tồn tại
    """
    if category in MAPPING:
        if keyword not in MAPPING[category]:
            MAPPING[category].append(keyword)
            logger.info(f"Đã thêm từ khóa '{keyword}' vào category '{category}'")
        return True
    else:
        logger.warning(f"Category '{category}' không tồn tại")
        return False


def validate_chunk_category(chunk_content: str, assigned_category: str) -> Tuple[bool, str]:
    """
    Kiểm tra xem chunk có chứa nhiều category hay không.
    
    Args:
        chunk_content: Nội dung của chunk
        assigned_category: Category đã được gán
        
    Returns:
        Tuple (is_valid, suggested_category)
        - is_valid: True nếu chunk chỉ chứa 1 category
        - suggested_category: Category được đề xuất nếu có conflict
    """
    if not chunk_content or not assigned_category:
        return True, assigned_category
    
    # Chuẩn hóa nội dung để kiểm tra
    content_lower = chunk_content.lower()
    
    # Tìm tất cả category có thể khớp với nội dung
    matching_categories = []
    for category, keywords in MAPPING.items():
        for keyword in keywords:
            if keyword in content_lower:
                matching_categories.append(category)
                break
    
    # Nếu chỉ có 1 category khớp và trùng với assigned_category
    if len(matching_categories) <= 1 and assigned_category in matching_categories:
        return True, assigned_category
    
    # Nếu có nhiều category khớp
    if len(matching_categories) > 1:
        logger.warning(f"Chunk chứa nhiều category: {matching_categories}")
        
        # Ưu tiên category theo thứ tự trong MAPPING
        for category in MAPPING.keys():
            if category in matching_categories:
                logger.info(f"Chọn category '{category}' thay vì '{assigned_category}'")
                return False, category
    
    # Nếu không có category nào khớp, giữ nguyên assigned_category
    return True, assigned_category


def fix_chunk_categories(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sửa các chunks có nhiều category để đảm bảo mỗi chunk chỉ có 1 category.
    
    Args:
        chunks: Danh sách chunks với metadata
        
    Returns:
        Danh sách chunks đã được sửa
    """
    if not chunks:
        return chunks
    
    fixed_chunks = []
    conflicts_fixed = 0
    
    for chunk in chunks:
        content = chunk.get('content', '')
        current_category = chunk.get('category', DEFAULT_CATEGORY)
        
        # Kiểm tra và sửa category nếu cần
        is_valid, suggested_category = validate_chunk_category(content, current_category)
        
        if not is_valid:
            conflicts_fixed += 1
            logger.info(f"Sửa category từ '{current_category}' thành '{suggested_category}'")
            chunk['category'] = suggested_category
        
        fixed_chunks.append(chunk)
    
    if conflicts_fixed > 0:
        logger.info(f"Đã sửa {conflicts_fixed} chunks có conflict category")
    
    return fixed_chunks


def classify_chunk_content(content: str, filename: str = "", use_llm: bool = False, api_key: str = None) -> Dict[str, Any]:
    """
    Phân loại category cho nội dung chunk dựa trên cả filename và content với tùy chọn LLM.
    Đảm bảo chỉ trả về 1 category duy nhất.
    
    Args:
        content: Nội dung của chunk
        filename: Tên file gốc (optional)
        use_llm: Có sử dụng LLM hay không (default: False)
        api_key: API key cho LLM (optional)
        
    Returns:
        Dict với category, confidence và method được sử dụng
    """
    if not content:
        return {
            'category': DEFAULT_CATEGORY,
            'confidence': 0.0,
            'method': 'error',
            'reasoning': 'Nội dung trống'
        }
    
    # Sử dụng LLM nếu được yêu cầu
    if use_llm:
        try:
            llm_service = get_llm_service(api_key)
            if llm_service.is_available():
                context = {
                    'filename': filename,
                    'content_length': len(content)
                }
                result = llm_service.classify_category(content, filename, context)
                logger.debug(f"LLM phân loại chunk: {result}")
                return {
                    'category': result['category'],
                    'confidence': result.get('confidence', 0.0),
                    'method': 'llm',
                    'reasoning': result.get('reasoning', 'LLM classification')
                }
            else:
                logger.warning("LLM service không có sẵn, fallback về rule-based")
        except Exception as e:
            logger.warning(f"Lỗi khi sử dụng LLM: {e}, fallback về rule-based")
    
    # Rule-based classification (fallback hoặc default)
    # Bước 1: Phân loại dựa trên filename (nếu có)
    filename_category = DEFAULT_CATEGORY
    if filename:
        filename_result = classify_by_filename(filename, use_llm=False)
        filename_category = filename_result['category']
    
    # Bước 2: Phân loại dựa trên content
    content_lower = content.lower()
    content_matches = []
    
    for category, keywords in MAPPING.items():
        for keyword in keywords:
            if keyword in content_lower:
                content_matches.append(category)
                break
    
    # Bước 3: Quyết định category cuối cùng
    if not content_matches:
        # Nếu content không khớp gì, dùng category từ filename
        final_category = filename_category
        confidence = 0.6  # Thấp hơn vì chỉ dựa vào filename
        reasoning = f"Dựa vào filename: {filename_category}"
    elif len(content_matches) == 1:
        # Nếu content chỉ khớp 1 category
        final_category = content_matches[0]
        confidence = 0.8
        reasoning = f"Khớp từ khóa trong content: {content_matches[0]}"
    else:
        # Nếu content khớp nhiều category, ưu tiên theo thứ tự trong MAPPING
        for category in MAPPING.keys():
            if category in content_matches:
                final_category = category
                break
        else:
            final_category = content_matches[0]
        confidence = 0.7  # Thấp hơn vì có conflict
        reasoning = f"Nhiều category khớp, chọn: {final_category}"
    
    # Bước 4: Validation cuối cùng
    is_valid, validated_category = validate_chunk_category(content, final_category)
    if not is_valid:
        final_category = validated_category
        confidence = 0.5  # Confidence thấp vì đã sửa
        reasoning += f" (đã sửa từ conflict)"
    
    logger.debug(f"Chunk classification: filename='{filename}', content_matches={content_matches}, final='{final_category}'")
    return {
        'category': final_category,
        'confidence': confidence,
        'method': 'rule_based',
        'reasoning': reasoning
    }


# Hàm tiện ích để test nhanh
def test_classification():
    """Test nhanh với một số file mẫu."""
    test_files = [
        "QĐ 580 - Quy chế TS và ĐT trình độ tiến sĩ ĐHCNTT&TT 2024.pdf",
        "Nghị định 81-2021-NĐ-CP miễn giảm học phí.pdf",
        "QĐ 861 danh sách xã KVIII 2021.pdf",
        "QĐ chuẩn đầu ra tin học ngoại ngữ.pdf",
        "Quyết định học bổng sinh viên ICTU.pdf",
        "Quy định rèn luyện sinh viên năm 2024.pdf",
        "Văn bản hợp nhất số 05.2021.QD.TTg.pdf",
        "QĐ 999 - Quy định gì đó không rõ keyword.pdf"
    ]
    
    print("=== TEST PHÂN LOẠI CATEGORY (RULE-BASED) ===")
    for filename in test_files:
        result = classify_by_filename(filename, use_llm=False)
        print(f"{filename:<60} -> {result['category']} (confidence: {result['confidence']:.2f})")
    
    print(f"\nTổng số category có sẵn: {len(get_available_categories())}")
    print(f"Danh sách: {get_available_categories()}")


def test_llm_classification():
    """Test phân loại với LLM."""
    test_files = [
        "QĐ 580 - Quy chế TS và ĐT trình độ tiến sĩ ĐHCNTT&TT 2024.pdf",
        "Nghị định 81-2021-NĐ-CP miễn giảm học phí.pdf",
        "QĐ chuẩn đầu ra tin học ngoại ngữ.pdf"
    ]
    
    print("\n=== TEST PHÂN LOẠI CATEGORY (LLM) ===")
    for filename in test_files:
        result = classify_by_filename(filename, use_llm=True)
        print(f"{filename:<60} -> {result['category']} (confidence: {result['confidence']:.2f}, method: {result['method']})")
        print(f"  Reasoning: {result['reasoning']}")


def test_chunk_classification():
    """Test phân loại chunk với LLM."""
    test_cases = [
        ("Quy định tuyển sinh đại học năm 2024", "QĐ tuyển sinh.pdf"),
        ("Đào tạo thạc sĩ và tiến sĩ", "QĐ đào tạo sau đại học.pdf"),
        ("Học phí và miễn giảm học phí", "Nghị định học phí.pdf"),
        ("Thực tập tốt nghiệp tại doanh nghiệp", "QĐ thực tập.pdf"),
        ("Nội dung không rõ category", "QĐ không rõ.pdf")
    ]
    
    print("\n=== TEST CHUNK CLASSIFICATION (RULE-BASED) ===")
    for content, filename in test_cases:
        result = classify_chunk_content(content, filename, use_llm=False)
        print(f"Content: {content}")
        print(f"Filename: {filename}")
        print(f"Classified as: {result['category']} (confidence: {result['confidence']:.2f})")
        print(f"Reasoning: {result['reasoning']}")
        print("-" * 50)
    
    print("\n=== TEST CHUNK CLASSIFICATION (LLM) ===")
    for content, filename in test_cases:
        result = classify_chunk_content(content, filename, use_llm=True)
        print(f"Content: {content}")
        print(f"Filename: {filename}")
        print(f"Classified as: {result['category']} (confidence: {result['confidence']:.2f}, method: {result['method']})")
        print(f"Reasoning: {result['reasoning']}")
        print("-" * 50)


def test_chunk_validation():
    """Test validation cho chunks."""
    print("\n=== TEST CHUNK VALIDATION ===")
    
    test_chunks = [
        {
            'content': 'Quy định về tuyển sinh và học phí sinh viên năm 2024',
            'category': 'admissions'
        },
        {
            'content': 'Đào tạo thạc sĩ và tiến sĩ tại trường đại học',
            'category': 'postgraduate_training'
        },
        {
            'content': 'Quy định về học phí và miễn giảm học phí cho sinh viên',
            'category': 'finance_and_tuition'
        },
        {
            'content': 'Học bổng và trợ cấp cho sinh viên nghèo',
            'category': 'scholarships'  # Có thể conflict với social_policy
        }
    ]
    
    for i, chunk in enumerate(test_chunks):
        print(f"\nChunk {i+1}:")
        print(f"Content: {chunk['content']}")
        print(f"Original category: {chunk['category']}")
        
        is_valid, suggested = validate_chunk_category(chunk['content'], chunk['category'])
        print(f"Valid: {is_valid}, Suggested: {suggested}")
        
        if not is_valid:
            print(f"[WARNING] Conflict detected! Fixed to: {suggested}")
    
    # Test fix_chunk_categories
    print(f"\n=== TEST FIX CHUNK CATEGORIES ===")
    fixed_chunks = fix_chunk_categories(test_chunks)
    for i, chunk in enumerate(fixed_chunks):
        print(f"Chunk {i+1}: {chunk['category']}")


def test_chunk_classification():
    """Test phân loại chunk dựa trên content."""
    print("\n=== TEST CHUNK CLASSIFICATION ===")
    
    test_cases = [
        ("Quy định tuyển sinh đại học năm 2024", "QĐ tuyển sinh.pdf"),
        ("Đào tạo thạc sĩ và tiến sĩ", "QĐ đào tạo sau đại học.pdf"),
        ("Học phí và miễn giảm học phí", "Nghị định học phí.pdf"),
        ("Thực tập tốt nghiệp tại doanh nghiệp", "QĐ thực tập.pdf"),
        ("Nội dung không rõ category", "QĐ không rõ.pdf")
    ]
    
    for content, filename in test_cases:
        category = classify_chunk_content(content, filename)
        print(f"Content: {content}")
        print(f"Filename: {filename}")
        print(f"Classified as: {category}")
        print("-" * 50)


def ensure_single_category_per_chunk(chunks: List[Dict[str, Any]], filename: str = "") -> List[Dict[str, Any]]:
    """
    Hàm wrapper để đảm bảo mỗi chunk chỉ có 1 category.
    Tích hợp vào các splitter hiện có.
    
    Args:
        chunks: Danh sách chunks từ splitter
        filename: Tên file gốc (optional)
        
    Returns:
        Danh sách chunks đã được validate và sửa
    """
    if not chunks:
        return chunks
    
    logger.info(f"Validating {len(chunks)} chunks for single category constraint")
    
    # Bước 1: Sửa các chunks có conflict category
    fixed_chunks = fix_chunk_categories(chunks)
    
    # Bước 2: Đảm bảo mỗi chunk có category hợp lệ
    validated_chunks = []
    for chunk in fixed_chunks:
        content = chunk.get('content', '')
        current_category = chunk.get('category', DEFAULT_CATEGORY)
        
        # Nếu chunk không có category hoặc category không hợp lệ
        if not current_category or current_category not in get_available_categories():
            # Phân loại lại dựa trên content và filename
            new_category = classify_chunk_content(content, filename)
            chunk['category'] = new_category
            logger.info(f"Re-classified chunk with invalid category to: {new_category}")
        
        validated_chunks.append(chunk)
    
    # Bước 3: Log thống kê
    category_counts = {}
    for chunk in validated_chunks:
        category = chunk.get('category', DEFAULT_CATEGORY)
        category_counts[category] = category_counts.get(category, 0) + 1
    
    logger.info(f"Final category distribution: {category_counts}")
    return validated_chunks


def validate_and_fix_chunk_metadata(chunk: Dict[str, Any], filename: str = "") -> Dict[str, Any]:
    """
    Validate và sửa metadata của một chunk để đảm bảo chỉ có 1 category.
    
    Args:
        chunk: Chunk cần validate
        filename: Tên file gốc (optional)
        
    Returns:
        Chunk đã được validate và sửa
    """
    if not chunk:
        return chunk
    
    content = chunk.get('content', '')
    current_category = chunk.get('category', DEFAULT_CATEGORY)
    
    # Validate category
    is_valid, suggested_category = validate_chunk_category(content, current_category)
    
    if not is_valid:
        logger.info(f"Fixed chunk category from '{current_category}' to '{suggested_category}'")
        chunk['category'] = suggested_category
    elif not current_category or current_category not in get_available_categories():
        # Nếu category không hợp lệ, phân loại lại
        new_category = classify_chunk_content(content, filename)
        chunk['category'] = new_category
        logger.info(f"Re-classified chunk with invalid category to: {new_category}")
    
    return chunk


if __name__ == "__main__":
    # Chạy tất cả test khi chạy trực tiếp file
    test_classification()
    test_llm_classification()
    test_chunk_classification()
    test_chunk_validation()
