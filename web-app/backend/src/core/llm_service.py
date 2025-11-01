#!/usr/bin/env python3
"""
LLM Service cho OpenAI GPT-4o API
Chức năng chính: Tạo từ khóa chính từ title tài liệu
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import OpenAI dynamically
openai_client = None
OPENAI_AVAILABLE = False
try:
    import openai  # type: ignore
    from openai import OpenAI  # type: ignore
    OPENAI_AVAILABLE = True
except Exception as e:
    OPENAI_AVAILABLE = False
    logger.warning(f"openai SDK không có sẵn: {e}")

@dataclass
class LLMConfig:
    """Cấu hình cho LLM calls"""
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 50  # Giảm xuống vì chỉ cần 3-5 từ
    model_name: str = "gpt-4o-mini"  # GPT-4o mini

class OpenAIService:
    """
    Service để gọi OpenAI API
    Chức năng chính: Tạo từ khóa chính từ title tài liệu
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        Khởi tạo OpenAI service
        
        Args:
            api_key: OpenAI API key
            config: Cấu hình LLM
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.config = config or LLMConfig()
        
        # Kiểm tra API key và SDK
        self.enabled = bool(self.api_key) and OPENAI_AVAILABLE
        
        self._oa_client = None

        if self.enabled:
            try:
                # Khởi tạo OpenAI client
                self._oa_client = OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI LLM ({self.config.model_name}) đã khởi tạo thành công")
            except Exception as e:
                logger.error(f"Không thể khởi tạo OpenAI client: {e}")
                self._oa_client = None
                self.enabled = False
        else:
            self.enabled = False
            if not OPENAI_AVAILABLE:
                logger.warning("openai SDK không được cài đặt")
            if not self.api_key:
                logger.warning("OPENAI_API_KEY chưa được thiết lập")
    
    def is_available(self) -> bool:
        """Kiểm tra xem LLM service có sẵn không"""
        return self.enabled and self._oa_client is not None
    
    def generate_keyword_from_title(self, title: str) -> str:
        """
        Tạo từ khóa chính từ title tài liệu.
        
        Args:
            title: Title của tài liệu
            
        Returns:
            Từ khóa chính (3-5 từ tổng quan)
        """
        if not self.enabled or not title:
            # Fallback: lấy 5 từ đầu tiên từ title
            words = title.split()[:5]
            return ' '.join(words)
        
        try:
            # Prompt ngắn gọn
            prompt = f'Từ tiêu đề: "{title}"\n\nRút gọn thành 3-5 từ khóa tiếng Việt. Chỉ trả về từ khóa, không giải thích.'

            response = self.call_openai(prompt)
            
            if response and len(response.strip()) > 0:
                keyword = response.strip()
                logger.debug(f"Generated keyword from title '{title}': '{keyword}'")
                return keyword
            else:
                # Fallback nếu response rỗng
                words = title.split()[:5]
                return ' '.join(words)
                
        except Exception as e:
            logger.warning(f"Lỗi khi tạo keyword từ LLM: {e}")
            # Fallback
            words = title.split()[:5]
            return ' '.join(words)
    
    def call_openai(self, prompt: str) -> str:
        """Gọi OpenAI (gpt-4o-mini) để sinh keyword."""
        if not self.enabled:
            raise Exception("OpenAI LLM service không có sẵn")

        if not self._oa_client:
            logger.error("OpenAI client chưa được khởi tạo!")
            raise Exception("OpenAI client chưa được khởi tạo. Kiểm tra lại API key và SDK.")

        try:
            model_name = self.config.model_name or 'gpt-4o-mini'
            
            # Sử dụng Chat Completions API
            completion = self._oa_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý trích xuất từ khóa tiếng Việt từ tiêu đề tài liệu. Chỉ trả về từ khóa, không giải thích."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            # Trích xuất text từ response
            if completion.choices and len(completion.choices) > 0:
                message = completion.choices[0].message
                text = message.content if message else None
                if text and text.strip():
                    return text.strip()
            
            # Fallback nếu không có text
            logger.warning("OpenAI response không có content")
            raise Exception("OpenAI response empty")
            
        except Exception as e:
            logger.error(f"Lỗi khi gọi OpenAI: {e}")
            raise


# Singleton instance
_llm_service_instance = None

def get_llm_service(api_key: Optional[str] = None, config: Optional[LLMConfig] = None) -> OpenAIService:
    """
    Lấy singleton instance của LLM service
    
    Args:
        api_key: OpenAI API key
        config: Cấu hình LLM
        
    Returns:
        OpenAIService instance
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = OpenAIService(api_key, config)
    
    return _llm_service_instance
