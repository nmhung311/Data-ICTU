#!/usr/bin/env python3
"""
LLM Service cho Gemini 2.5 Flash
Tích hợp Gemini API để cải thiện độ linh hoạt trong việc chia metadata và phân loại category

Author: AI Assistant
Date: 2024
"""

import os
import logging
import importlib.util
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import json
import re

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Gemini dynamically
genai = None
try:
    spec = importlib.util.find_spec("google.generativeai")
    if spec is not None:
        genai = importlib.import_module("google.generativeai")
        GEMINI_AVAILABLE = True
    else:
        GEMINI_AVAILABLE = False
        logger.warning("google-generativeai không có sẵn. Chế độ LLM sẽ bị tắt.")
except Exception as e:
    GEMINI_AVAILABLE = False
    logger.warning(f"google-generativeai không có sẵn: {e}. Chế độ LLM sẽ bị tắt.")

@dataclass
class LLMConfig:
    """Cấu hình cho LLM calls"""
    temperature: float = 0.0  # Deterministic
    top_p: float = 1.0
    max_output_tokens: int = 1000
    model_name: str = "gemini-2.5-flash"

@dataclass
class DocumentMetadata:
    """Metadata của document block"""
    doc_id: str
    data_type: str
    category: str
    date: str
    source: str
    content: str
    confidence: float = 0.0  # Độ tin cậy của phân loại

class GeminiService:
    """
    Service để gọi Gemini 2.5 Flash API
    Cung cấp các method để chia metadata và phân loại category linh hoạt
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        Khởi tạo Gemini service
        
        Args:
            api_key: Google API key
            config: Cấu hình LLM
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.config = config or LLMConfig()
        self.enabled = GEMINI_AVAILABLE and bool(self.api_key)
        
        if self.enabled and genai is not None:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.config.model_name)
                logger.info("Gemini LLM service đã khởi tạo thành công")
            except Exception as e:
                logger.warning(f"Không thể khởi tạo Gemini LLM: {e}")
                self.enabled = False
        else:
            self.enabled = False
            logger.warning("Gemini LLM service bị tắt")
    
    def is_available(self) -> bool:
        """Kiểm tra xem LLM service có sẵn không"""
        return self.enabled
    
    def call_gemini(self, prompt: str, config_override: Optional[LLMConfig] = None) -> str:
        """
        Gọi Gemini API với prompt
        
        Args:
            prompt: Prompt để gửi đến Gemini
            config_override: Override config nếu cần
            
        Returns:
            Response từ Gemini
        """
        if not self.enabled:
            raise Exception("Gemini LLM service không có sẵn")
        
        config = config_override or self.config
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=config.temperature,
                    top_p=config.top_p,
                    max_output_tokens=config.max_output_tokens
                )
            )
            
            # Xử lý response theo nhiều format khác nhau
            return self._extract_response_text(response)
            
        except Exception as e:
            logger.error(f"Lỗi khi gọi Gemini API: {e}")
            raise
    
    def _extract_response_text(self, response) -> str:
        """Trích xuất text từ response của Gemini"""
        try:
            # Thử accessor đơn giản trước
            if hasattr(response, 'text'):
                return response.text.strip()
        except Exception:
            pass
        
        try:
            # Thử access parts trực tiếp
            if hasattr(response, 'parts') and response.parts:
                return ''.join(part.text for part in response.parts if hasattr(part, 'text')).strip()
        except Exception:
            pass
        
        try:
            # Thử access candidates
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    return ''.join(part.text for part in candidate.content.parts if hasattr(part, 'text')).strip()
        except Exception:
            pass
        
        return ""  # Fallback
    
    def classify_category(self, content: str, filename: str = "", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Phân loại category cho content sử dụng LLM
        
        Args:
            content: Nội dung cần phân loại
            filename: Tên file (optional)
            context: Context bổ sung (optional)
            
        Returns:
            Dict với category và confidence
        """
        if not self.enabled:
            return {
                'category': 'training_and_regulations',
                'confidence': 0.0,
                'reasoning': 'LLM không có sẵn'
            }
        
        # Tạo prompt cho phân loại category
        prompt = self._create_category_prompt(content, filename, context)
        
        try:
            response = self.call_gemini(prompt)
            return self._parse_category_response(response)
        except Exception as e:
            logger.warning(f"Lỗi phân loại category với LLM: {e}")
            return {
                'category': 'training_and_regulations',
                'confidence': 0.0,
                'reasoning': f'Lỗi LLM: {str(e)}'
            }
    
    def _create_category_prompt(self, content: str, filename: str, context: Dict[str, Any]) -> str:
        """Tạo prompt cho phân loại category"""
        # Taxonomy cố định
        taxonomy = [
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
        
        # Context info
        context_info = ""
        if context:
            context_info = f"\nContext: {json.dumps(context, ensure_ascii=False)}"
        
        prompt = f"""Bạn là một chuyên gia phân loại văn bản pháp lý Việt Nam. Nhiệm vụ của bạn:

1. Phân tích nội dung văn bản và phân loại vào đúng category
2. Trả về kết quả theo format JSON chuẩn
3. Sử dụng temperature=0.0 để đảm bảo kết quả deterministic

======================
DANH SÁCH CATEGORY CHO PHÉP
======================
{json.dumps(taxonomy, ensure_ascii=False)}

======================
HƯỚNG DẪN PHÂN LOẠI
======================
- "tuyển sinh/xét tuyển/điều kiện dự tuyển" → admissions
- "tiến sĩ/thạc sĩ/đào tạo sau đại học/TS/ThS" → postgraduate_training  
- "học phí/miễn giảm/thu/chi/quy định phí" → finance_and_tuition
- "kỳ thi/thi cử/đánh giá/kiểm tra" → examination
- "thực tập/TTTN/doanh nghiệp/internship" → internship
- "đào tạo từ xa/e-learning/online/qua mạng" → distance_learning
- "công tác sinh viên/khen thưởng/kỷ luật/học bổng/rèn luyện" → student_affairs
- "tổ chức cán bộ/nhân sự/CBVC" → human_resources
- "phòng đào tạo/chương trình học/tín chỉ/kế hoạch giảng dạy/GDTC/thể chất/quy chế" → academic_affairs
- Khác → training_and_regulations

======================
THÔNG TIN ĐẦU VÀO
======================
Filename: {filename}{context_info}

Content: {content[:2000]}...

======================
FORMAT OUTPUT
======================
Trả về JSON với format:
{{
    "category": "tên_category",
    "confidence": 0.95,
    "reasoning": "lý do phân loại",
    "keywords_found": ["từ_khóa_1", "từ_khóa_2"]
}}

======================
OUTPUT
======================
"""
        return prompt
    
    def _parse_category_response(self, response: str) -> Dict[str, Any]:
        """Parse response từ LLM thành dict"""
        try:
            # Tìm JSON trong response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # Validate category
                valid_categories = [
                    'training_and_regulations', 'academic_affairs', 'admissions',
                    'finance_and_tuition', 'examination', 'postgraduate_training',
                    'internship', 'student_affairs', 'human_resources', 'distance_learning'
                ]
                
                if result.get('category') not in valid_categories:
                    result['category'] = 'training_and_regulations'
                
                return result
        except Exception as e:
            logger.warning(f"Lỗi parse JSON response: {e}")
        
        # Fallback
        return {
            'category': 'training_and_regulations',
            'confidence': 0.0,
            'reasoning': 'Không thể parse response',
            'keywords_found': []
        }
    
    def extract_metadata(self, content: str, filename: str = "", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Trích xuất metadata từ content sử dụng LLM
        
        Args:
            content: Nội dung cần trích xuất metadata
            filename: Tên file (optional)
            context: Context bổ sung (optional)
            
        Returns:
            Dict với metadata đã trích xuất
        """
        if not self.enabled:
            return self._extract_metadata_fallback(content, filename)
        
        prompt = self._create_metadata_prompt(content, filename, context)
        
        try:
            response = self.call_gemini(prompt)
            return self._parse_metadata_response(response, content)
        except Exception as e:
            logger.warning(f"Lỗi trích xuất metadata với LLM: {e}")
            return self._extract_metadata_fallback(content, filename)
    
    def _create_metadata_prompt(self, content: str, filename: str, context: Dict[str, Any]) -> str:
        """Tạo prompt cho trích xuất metadata"""
        context_info = ""
        if context:
            context_info = f"\nContext: {json.dumps(context, ensure_ascii=False)}"
        
        prompt = f"""Bạn là một chuyên gia trích xuất metadata từ văn bản pháp lý Việt Nam. Nhiệm vụ:

1. Trích xuất các thông tin metadata quan trọng từ văn bản
2. Xác định loại văn bản và nguồn gốc
3. Trả về kết quả theo format JSON chuẩn

======================
THÔNG TIN ĐẦU VÀO
======================
Filename: {filename}{context_info}

Content: {content[:3000]}...

======================
FORMAT OUTPUT
======================
Trả về JSON với format:
{{
    "doc_id": "số hiệu văn bản",
    "data_type": "loại dữ liệu",
    "date": "ngày tháng năm",
    "source": "nguồn gốc văn bản",
    "document_type": "loại văn bản",
    "keywords": ["từ_khóa_1", "từ_khóa_2"],
    "summary": "tóm tắt ngắn gọn"
}}

======================
HƯỚNG DẪN TRÍCH XUẤT
======================
- doc_id: Tìm số hiệu văn bản (VD: 429/QĐ-ĐHCNTT&TT)
- data_type: Thường là "markdown" hoặc "document"
- date: Format yyyy-mm-dd
- source: Tên cơ quan ban hành hoặc nguồn gốc
- document_type: Quyết định, Thông tư, Nghị định, etc.
- keywords: Các từ khóa quan trọng trong văn bản
- summary: Tóm tắt nội dung chính trong 1-2 câu

======================
OUTPUT
======================
"""
        return prompt
    
    def _parse_metadata_response(self, response: str, content: str) -> Dict[str, Any]:
        """Parse metadata response từ LLM"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # Validate và clean up
                result['doc_id'] = result.get('doc_id', '')
                result['data_type'] = result.get('data_type', 'markdown')
                result['date'] = result.get('date', '')
                result['source'] = result.get('source', '')
                result['document_type'] = result.get('document_type', '')
                result['keywords'] = result.get('keywords', [])
                result['summary'] = result.get('summary', '')
                
                return result
        except Exception as e:
            logger.warning(f"Lỗi parse metadata response: {e}")
        
        return self._extract_metadata_fallback(content, "")
    
    def _extract_metadata_fallback(self, content: str, filename: str) -> Dict[str, Any]:
        """Fallback method khi LLM không có sẵn"""
        # Sử dụng regex đơn giản để trích xuất
        doc_id = ""
        date = ""
        
        # Tìm doc_id
        doc_id_match = re.search(r'Số\s*:\s*([A-Z0-9ĐƠƯ/.\-–&]+)', content, re.IGNORECASE)
        if doc_id_match:
            doc_id = doc_id_match.group(1).strip()
        
        # Tìm date
        date_match = re.search(r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', content, re.IGNORECASE)
        if date_match:
            day, month, year = date_match.groups()
            date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return {
            'doc_id': doc_id,
            'data_type': 'markdown',
            'date': date,
            'source': filename or 'Tài liệu pháp lý',
            'document_type': 'Quyết định',
            'keywords': [],
            'summary': content[:200] + '...' if len(content) > 200 else content
        }
    
    def split_content_intelligently(self, content: str, filename: str = "", context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chia content thành các blocks thông minh sử dụng LLM
        
        Args:
            content: Nội dung cần chia
            filename: Tên file (optional)
            context: Context bổ sung (optional)
            
        Returns:
            List các blocks với metadata
        """
        if not self.enabled:
            return self._split_content_fallback(content, filename)
        
        prompt = self._create_split_prompt(content, filename, context)
        
        try:
            response = self.call_gemini(prompt)
            return self._parse_split_response(response, content)
        except Exception as e:
            logger.warning(f"Lỗi chia content với LLM: {e}")
            return self._split_content_fallback(content, filename)
    
    def _create_split_prompt(self, content: str, filename: str, context: Dict[str, Any]) -> str:
        """Tạo prompt cho việc chia content"""
        context_info = ""
        if context:
            context_info = f"\nContext: {json.dumps(context, ensure_ascii=False)}"
        
        prompt = f"""Bạn là một chuyên gia chia văn bản pháp lý Việt Nam thành các blocks logic. Nhiệm vụ:

1. Chia văn bản thành các phần logic (Điều, Khoản, Chương, etc.)
2. Mỗi phần phải có metadata đầy đủ
3. Trả về kết quả theo format JSON

======================
THÔNG TIN ĐẦU VÀO
======================
Filename: {filename}{context_info}

Content: {content[:4000]}...

======================
FORMAT OUTPUT
======================
Trả về JSON array với format:
[
    {{
        "block_type": "legal_basis|quyet_dinh|article|khoan|chuong|phu_luc",
        "title": "tiêu đề block",
        "content": "nội dung block",
        "source": "nguồn gốc",
        "metadata": {{
            "doc_id": "số hiệu văn bản",
            "data_type": "markdown",
            "category": "category_name",
            "date": "yyyy-mm-dd",
            "source": "nguồn gốc"
        }}
    }}
]

======================
HƯỚNG DẪN CHIA BLOCK
======================
- legal_basis: Phần "Căn cứ", "Theo"
- quyet_dinh: Phần "QUYẾT ĐỊNH" 
- article: Các "Điều"
- khoan: Các "Khoản" trong Điều
- chuong: Các "Chương"
- phu_luc: Các "Phụ lục"

Mỗi block phải có:
- block_type: Loại block
- title: Tiêu đề ngắn gọn
- content: Nội dung đầy đủ
- source: Nguồn gốc (VD: "Điều 1", "Căn cứ", etc.)
- metadata: Thông tin metadata đầy đủ

======================
OUTPUT
======================
"""
        return prompt
    
    def _parse_split_response(self, response: str, original_content: str) -> List[Dict[str, Any]]:
        """Parse split response từ LLM"""
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                blocks = json.loads(json_str)
                
                # Validate và clean up blocks
                validated_blocks = []
                for block in blocks:
                    if isinstance(block, dict) and 'content' in block:
                        validated_block = {
                            'block_type': block.get('block_type', 'article'),
                            'title': block.get('title', ''),
                            'content': block.get('content', ''),
                            'source': block.get('source', ''),
                            'metadata': block.get('metadata', {})
                        }
                        validated_blocks.append(validated_block)
                
                return validated_blocks
        except Exception as e:
            logger.warning(f"Lỗi parse split response: {e}")
        
        return self._split_content_fallback(original_content, "")
    
    def _split_content_fallback(self, content: str, filename: str) -> List[Dict[str, Any]]:
        """Fallback method khi LLM không có sẵn"""
        # Chia đơn giản theo các pattern cơ bản
        blocks = []
        
        # Tìm các Điều
        article_matches = list(re.finditer(r'Điều\s+(\d+)\.?\s*(.*)', content, re.IGNORECASE))
        
        for i, match in enumerate(article_matches):
            article_num = match.group(1)
            article_title = match.group(2).strip()
            
            # Xác định ranh giới của Điều này
            start_pos = match.start()
            if i + 1 < len(article_matches):
                end_pos = article_matches[i + 1].start()
            else:
                end_pos = len(content)
            
            article_content = content[start_pos:end_pos].strip()
            
            blocks.append({
                'block_type': 'article',
                'title': f"Điều {article_num}",
                'content': article_content,
                'source': f"Điều {article_num}",
                'metadata': {
                    'doc_id': '',
                    'data_type': 'markdown',
                    'category': 'training_and_regulations',
                    'date': '',
                    'source': f"Điều {article_num}"
                }
            })
        
        return blocks


# Singleton instance
_llm_service_instance = None

def get_llm_service(api_key: Optional[str] = None, config: Optional[LLMConfig] = None) -> GeminiService:
    """
    Lấy singleton instance của LLM service
    
    Args:
        api_key: Google API key
        config: Cấu hình LLM
        
    Returns:
        GeminiService instance
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = GeminiService(api_key, config)
    
    return _llm_service_instance


def test_llm_service():
    """Test function cho LLM service"""
    print("=== TEST LLM SERVICE ===")
    
    service = get_llm_service()
    
    if not service.is_available():
        print("LLM service không có sẵn")
        return
    
    # Test classify category
    test_content = "Quy định về tuyển sinh đại học năm 2024, bao gồm các điều kiện dự tuyển và phương thức xét tuyển"
    result = service.classify_category(test_content, "QĐ tuyển sinh.pdf")
    print(f"Category classification: {result}")
    
    # Test extract metadata
    test_doc = """
    ĐẠI HỌC THÁI NGUYÊN
    TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG
    Số: 429/QĐ-ĐHCNTT&TT
    Thái Nguyên, ngày 22 tháng 6 năm 2022
    QUYẾT ĐỊNH
    Về việc ban hành Quy định việc biên soạn, lựa chọn, thẩm định, duyệt và sử dụng tài liệu giảng dạy
    """
    
    metadata = service.extract_metadata(test_doc, "QĐ 429.pdf")
    print(f"Metadata extraction: {metadata}")


if __name__ == "__main__":
    test_llm_service()
