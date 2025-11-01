#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keyword Generator for Vietnamese Legal Documents

Extracts keywords from document titles using LLM or fallback methods.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class KeywordGenerator:
    """
    Generate keywords from document titles.
    Uses LLM if available, otherwise uses fallback methods.
    """
    
    def __init__(self, llm_service=None, use_llm: bool = True):
        """
        Initialize keyword generator.
        
        Args:
            llm_service: LLM service instance (optional)
            use_llm: Whether to use LLM for keyword generation
        """
        self.llm_service = llm_service
        self.use_llm = use_llm
        self.llm_enabled = llm_service.is_available() if llm_service else False
        self.cached_keyword = None  # Cache for the document keyword
    
    def generate_keyword(self, document_title: str) -> str:
        """
        Generate keyword from document title.
        
        Args:
            document_title: The document title
            
        Returns:
            Keyword string
        """
        # Reset cache if title changed (for same instance reuse)
        # Note: Cache chỉ dùng cho cùng một document, không cache cross-document
        # Nếu title mới, reset cache
        if self.cached_keyword is not None and not hasattr(self, '_cached_title'):
            self.cached_keyword = None
        
        # Return cached keyword if same title
        if (self.cached_keyword is not None and 
            hasattr(self, '_cached_title') and 
            self._cached_title == document_title):
            return self.cached_keyword
        
        # Use LLM service to generate keyword
        if self.use_llm and self.llm_enabled and self.llm_service and document_title:
            try:
                keyword = self.llm_service.generate_keyword_from_title(document_title)
                logger.info(f"Generated keyword from title: '{keyword}'")
            except Exception as e:
                logger.warning(f"LLM failed to generate keyword: {e}. Using fallback.")
                # Fallback: Extract first 5 words from title
                keyword = self._fallback_keyword(document_title)
        else:
            # Fallback when LLM not available
            keyword = self._fallback_keyword(document_title)
        
        # Cache the keyword với title tương ứng
        self.cached_keyword = keyword
        self._cached_title = document_title
        return keyword
    
    def _fallback_keyword(self, document_title: str) -> str:
        """
        Fallback method to generate keyword when LLM is not available.
        Extracts first 5 words from title (3-5 words for summary).
        
        Args:
            document_title: The document title
            
        Returns:
            Keyword string (first 5 words)
        """
        words = document_title.split()
        return ' '.join(words[:5])
    
    def reset_cache(self):
        """Reset cached keyword."""
        self.cached_keyword = None
        if hasattr(self, '_cached_title'):
            delattr(self, '_cached_title')


def get_keyword_generator(llm_service=None, use_llm: bool = True) -> KeywordGenerator:
    """
    Factory function to create a KeywordGenerator instance.
    
    Args:
        llm_service: LLM service instance (optional)
        use_llm: Whether to use LLM for keyword generation
        
    Returns:
        KeywordGenerator instance
    """
    return KeywordGenerator(llm_service, use_llm)

