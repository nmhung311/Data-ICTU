"""
Metadata extraction agent for Raw2MD Agent.

Hybrid approach using regex patterns and Gemini 2.5 Flash LLM for Vietnamese
administrative document metadata extraction.
"""

import re
import json
import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai  # type: ignore  # pyright: ignore[reportMissingImports]
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not available. LLM mode will be disabled.")

try:
    import redis  # type: ignore  # pyright: ignore[reportMissingImports]
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis not available. Caching will be disabled.")


@dataclass
class MetadataResult:
    """Result of metadata extraction."""
    doc_id: str
    category: str
    source: str
    date: str
    modify: str
    partial_mod: bool
    data_type: str
    amend: str    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'doc_id': self.doc_id,
            'category': self.category,
            'source': self.source,
            'date': self.date,
            'modify': self.modify,
            'partial_mod': self.partial_mod,
            'data_type': self.data_type,
            'amend': self.amend,
        }


class MetadataAgent:
    """
    Metadata extraction agent with hybrid regex + LLM approach.
    
    Features:
    - Regex-based fast extraction
    - Gemini 2.5 Flash LLM integration
    - Redis caching for performance
    - Vietnamese administrative document patterns
    - Hybrid mode with fallback strategies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metadata agent.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # LLM configuration
        self.llm_enabled = GEMINI_AVAILABLE and self.config.get('llm_enabled', True)
        self.api_key = self.config.get('api_key')
        self.model = self.config.get('model', 'gemini-2.5-flash')
        self.temperature = self.config.get('temperature', 0.0)
        self.max_tokens = self.config.get('max_tokens', 500)
        self.timeout = self.config.get('timeout', 30)
        
        # Cache configuration
        self.cache_enabled = REDIS_AVAILABLE and self.config.get('cache_enabled', True)
        self.redis_client = None
        self.cache_ttl = self.config.get('cache_ttl', 2592000)  # 30 days
        
        # Initialize components
        self._initialize_llm()
        self._initialize_cache()
        
        # Regex patterns for Vietnamese administrative documents
        self._compile_patterns()
    
    def _initialize_llm(self) -> None:
        """Initialize Gemini LLM client."""
        if not self.llm_enabled:
            logger.info("LLM mode disabled")
            return
        
        if not self.api_key:
            logger.warning("Google API key not provided, LLM mode disabled")
            self.llm_enabled = False
            return
        
        try:
            genai.configure(api_key=self.api_key)
            logger.info(f"Gemini LLM initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}")
            self.llm_enabled = False
    
    def _initialize_cache(self) -> None:
        """Initialize Redis cache client."""
        if not self.cache_enabled:
            logger.info("Caching disabled")
            return
        
        try:
            redis_url = self.config.get('redis_url', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")
            self.cache_enabled = False
            self.redis_client = None
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for Vietnamese documents."""
        self.patterns = {
            # Header patterns
            'header': re.compile(r'^(CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM|VIỆT NAM DÂN CHỦ CỘNG HÒA)', re.MULTILINE | re.IGNORECASE),
            
            # Document type patterns - more comprehensive
            'doc_type': re.compile(r'^(QUYẾT ĐỊNH|THÔNG TƯ|NGHỊ ĐỊNH|QUY ĐỊNH|CÔNG VĂN|THÔNG BÁO|CHỈ THỊ|NGHỊ QUYẾT)', re.MULTILINE | re.IGNORECASE),
            
            # Document number patterns - enhanced for Vietnamese documents
            'doc_number': re.compile(r'Số:\s*([^,\n]+)', re.IGNORECASE),
            'doc_number_alt': re.compile(r'(\d{1,4}/\d{4}/[A-ZĐƠƯ\-&]+/[A-ZĐƠƯ\-&]+|\d+[\/\-]\d+[\/\-]\d+)', re.IGNORECASE),
            'doc_number_pattern': re.compile(r'(\d+[\/\-]\d+[\/\-]\d+[\/\-]?[A-ZĐƠƯ\-&]*)', re.IGNORECASE),
            'doc_number_qd': re.compile(r'(QĐ[\/\-]\d+[\/\-]\d+[\/\-]?[A-ZĐƠƯ\-&]*)', re.IGNORECASE),
            'doc_number_tt': re.compile(r'(TT[\/\-]\d+[\/\-]\d+[\/\-]?[A-ZĐƠƯ\-&]*)', re.IGNORECASE),
            
            # Date patterns - more flexible
            'date_full': re.compile(r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', re.IGNORECASE),
            'date_short': re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})', re.IGNORECASE),
            'date_location': re.compile(r'([^,]+),\s*ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', re.IGNORECASE),
            
            # Issuing authority patterns
            'authority': re.compile(r'(BỘ\s+[^,\n]+|TRƯỜNG\s+[^,\n]+|UBND\s+[^,\n]+|CHÍNH PHỦ|THỦ TƯỚNG|HIỆU TRƯỞNG)', re.IGNORECASE),
            
            # Legal basis patterns - improved
            'legal_basis': re.compile(r'Căn cứ\s+([^;]+);', re.IGNORECASE | re.MULTILINE),
            
            # Article patterns - more precise and comprehensive
            'article': re.compile(r'Điều\s+(\d+)[\.:]?\s*([^Điều]+?)(?=Điều\s+\d+|Chương\s+[IVX\d]+|QUYẾT ĐỊNH|$)', re.IGNORECASE | re.DOTALL),
            'article_detailed': re.compile(r'Điều\s+(\d+)\.\s*([^Điều]+?)(?=Điều\s+\d+\.|Điều\s+\d+:|Chương\s+[IVX\d]+|QUYẾT ĐỊNH|$)', re.IGNORECASE | re.DOTALL),
            
            # Chapter patterns
            'chapter': re.compile(r'Chương\s+([IVX\d]+)[\.:]?\s*([^Chương]+?)(?=Chương\s+[IVX\d]+|$)', re.IGNORECASE | re.DOTALL),
            
            # Clause patterns (1., 2., 3.) - improved
            'clause': re.compile(r'(\d+)\.\s*([^0-9]+?)(?=\d+\.|Điều\s+\d+|Chương\s+[IVX\d]+|$)', re.MULTILINE | re.DOTALL),
            
            # Sub-clause patterns (a), b), c) - improved
            'sub_clause': re.compile(r'([a-z])\)\s*([^a-z)]+?)(?=[a-z]\)|\d+\.|Điều\s+\d+|$)', re.MULTILINE | re.DOTALL),
            
            # Signature patterns - improved
            'signature': re.compile(r'([A-Z][^,\n]+(?:TS\.|GS\.|PGS\.|ThS\.|CN\.)?[^,\n]*)', re.MULTILINE),
            
            # Title patterns - enhanced for Vietnamese administrative documents
            'title_keywords': re.compile(r'^(Về việc|Ban hành|Quy định|Hướng dẫn|Thực hiện|Sửa đổi|Bổ sung|Thay thế)', re.IGNORECASE),
            'title_modification': re.compile(r'(Sửa đổi|Bổ sung|Thay thế).*?(của|Quy định|Điều)', re.IGNORECASE),
            'title_about': re.compile(r'Về việc\s+([^,\n]+)', re.IGNORECASE),
            
            # Modification and amendment patterns
            'modify_keywords': re.compile(r'(Sửa đổi|Bổ sung|Thay thế|Điều chỉnh).*?(của|Quy định|Điều|Khoản)', re.IGNORECASE),
            'amend_keywords': re.compile(r'(Bãi bỏ|Hủy bỏ|Thay thế).*?(Quyết định|Thông tư|Nghị định)', re.IGNORECASE),
        }
        
        # Category mapping - updated
        self.category_mapping = {
            'training_and_regulations': ['Thông tư', 'Quy định', 'Hướng dẫn', 'Quy chế', 'Chương trình'],
            'decision': ['Quyết định', 'Công nhận', 'Bổ nhiệm', 'Ban hành'],
            'policy': ['Nghị định', 'Chính sách', 'Kế hoạch'],
            'announcement': ['Thông báo', 'Công văn', 'Kết luận', 'Giấy mời'],
        }
        
        # Document type mapping
        self.doc_type_mapping = {
            'QUYẾT ĐỊNH': 'decision',
            'THÔNG TƯ': 'training_and_regulations',
            'NGHỊ ĐỊNH': 'policy',
            'QUY ĐỊNH': 'training_and_regulations',
            'CÔNG VĂN': 'announcement',
            'THÔNG BÁO': 'announcement',
            'CHỈ THỊ': 'policy',
            'NGHỊ QUYẾT': 'policy',
        }
    
    def analyze_document(self, text: str, mode: str = 'hybrid') -> MetadataResult:
        """
        Analyze document and extract metadata.
        
        Args:
            text: Cleaned document text
            mode: Extraction mode ('regex', 'llm', 'hybrid')
            
        Returns:
            MetadataResult object
        """
        if not text or not text.strip():
            return self._create_empty_result()
        
        # Check cache first
        if self.cache_enabled:
            cached_result = self._get_from_cache(text)
            if cached_result:
                logger.debug("Using cached metadata result")
                return cached_result
        
        # Extract metadata based on mode
        if mode == 'regex':
            result = self._extract_with_regex(text)
        elif mode == 'llm':
            result = self._extract_with_llm(text)
        elif mode == 'hybrid':
            result = self._extract_with_hybrid(text)
        else:
            raise ValueError(f"Invalid extraction mode: {mode}")
        
        # Cache result
        if self.cache_enabled and result:
            self._save_to_cache(text, result)
        
        return result
    
    def _extract_with_regex(self, text: str) -> MetadataResult:
        """Extract metadata using improved regex patterns."""
        logger.debug("Extracting metadata with improved regex")
        
        # Extract basic metadata
        doc_id = self._extract_doc_id(text)
        date = self._extract_date(text)
        source = self._extract_source(text)
        category = self._extract_category(text)
        modify = self._extract_modify(text)
        amend = self._extract_amend(text)
        
        # Determine partial_mod
        partial_mod = bool(modify)
        
        return MetadataResult(
            doc_id=doc_id,
            category=category,
            source=source,
            date=date,
            modify=modify,
            partial_mod=partial_mod,
            data_type="markdown",
            amend=amend,
        )
    
    def _extract_with_llm(self, text: str) -> MetadataResult:
        """Extract metadata using Gemini LLM."""
        if not self.llm_enabled:
            logger.warning("LLM not available, falling back to regex")
            return self._extract_with_regex(text)
        
        logger.debug("Extracting metadata with LLM")
        
        try:
            # Prepare prompt
            prompt = self._create_llm_prompt(text)
            
            # Call Gemini API
            response = self._call_gemini_api(prompt)
            
            # Parse response
            result = self._parse_llm_response(response)
            
            return result
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}, falling back to regex")
            return self._extract_with_regex(text)
    
    def _extract_with_hybrid(self, text: str) -> MetadataResult:
        """Extract metadata using hybrid approach (regex + LLM fallback)."""
        logger.debug("Extracting metadata with hybrid approach")
        
        # Step 1: Extract with regex
        regex_result = self._extract_with_regex(text)
        
        # Step 2: Check if critical fields are missing
        critical_fields = ['doc_id', 'category', 'source', 'date']
        missing_fields = [field for field in critical_fields if not getattr(regex_result, field)]
        
        if not missing_fields:
            logger.debug("All critical fields found with regex")
            return regex_result
        
        # Step 3: Use LLM for missing fields
        if self.llm_enabled:
            logger.debug(f"Missing critical fields: {missing_fields}, using LLM")
            try:
                llm_result = self._extract_with_llm(text)
                
                # Merge results (LLM fills missing fields)
                merged_result = self._merge_results(regex_result, llm_result, missing_fields)
                return merged_result
                
            except Exception as e:
                logger.warning(f"LLM fallback failed: {e}")
        
        return regex_result
    
    def _extract_doc_id(self, text: str) -> str:
        """Extract document ID using enhanced regex patterns."""
        # Try "Số:" pattern first
        match = self.patterns['doc_number'].search(text)
        if match:
            doc_id = match.group(1).strip()
            if doc_id and len(doc_id) > 3:  # Avoid incomplete IDs
                return doc_id
        
        # Try QĐ pattern (Quyết định)
        match = self.patterns['doc_number_qd'].search(text)
        if match:
            return match.group(1)
        
        # Try TT pattern (Thông tư)
        match = self.patterns['doc_number_tt'].search(text)
        if match:
            return match.group(1)
        
        # Try general pattern
        match = self.patterns['doc_number_pattern'].search(text)
        if match:
            return match.group(1)
        
        # Try alternative pattern
        match = self.patterns['doc_number_alt'].search(text)
        if match:
            return match.group(1)
        
        return ""
    
    def _extract_date(self, text: str) -> str:
        """Extract date and convert to ISO format."""
        # Try location + date pattern first
        match = self.patterns['date_location'].search(text)
        if match:
            _, day, month, year = match.groups()
            try:
                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # Try full date pattern
        match = self.patterns['date_full'].search(text)
        if match:
            day, month, year = match.groups()
            try:
                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # Try short date pattern
        match = self.patterns['date_short'].search(text)
        if match:
            day, month, year = match.groups()
            try:
                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        return ""
    
    def _extract_source(self, text: str) -> str:
        """Extract document source/title with enhanced logic."""
        lines = text.split('\n')
        
        # Look for modification titles first (Sửa đổi, Bổ sung)
        for line in lines:
            line = line.strip()
            if self.patterns['title_modification'].search(line) and len(line) > 20:
                return line
        
        # Look for "Về việc" pattern
        for line in lines:
            line = line.strip()
            match = self.patterns['title_about'].search(line)
            if match and len(line) > 15:
                return line
        
        # Look for lines with title keywords
        for line in lines:
            line = line.strip()
            if self.patterns['title_keywords'].search(line) and len(line) > 15:
                return line
        
        # Look for lines with document type keywords
        for line in lines:
            line = line.strip()
            if self.patterns['doc_type'].search(line) and len(line) > 15:
                return line
        
        # Look for lines starting with "Về việc" or similar
        for line in lines:
            line = line.strip()
            if re.search(r'^(Về việc|Ban hành|Quy định|Hướng dẫn)', line, re.IGNORECASE):
                return line
        
        # Fallback: return first non-empty line that looks like a title
        for line in lines:
            line = line.strip()
            if line and len(line) > 15 and not re.match(r'^[A-Z\s]+$', line):  # Not all caps
                return line
        
        # Last resort: return first non-empty line
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:
                return line
        
        return ""
    
    def _extract_category(self, text: str) -> str:
        """Extract document category with improved logic."""
        # First try to match document type pattern
        match = self.patterns['doc_type'].search(text)
        if match:
            doc_type = match.group(1).upper()
            return self.doc_type_mapping.get(doc_type, 'general_document')
        
        # Fallback to keyword matching
        text_upper = text.upper()
        for category, keywords in self.category_mapping.items():
            for keyword in keywords:
                if keyword.upper() in text_upper:
                    return category
        
        return "general_document"
    
    def _extract_modify(self, text: str) -> str:
        """Extract modification information."""
        match = self.patterns['modify_keywords'].search(text)
        if match:
            return match.group(1)
        return ""
    
    def _extract_amend(self, text: str) -> str:
        """Extract amendment information."""
        match = self.patterns['amend_keywords'].search(text)
        if match:
            return match.group(1)
        return ""
    
    def _extract_document_structure(self, text: str) -> Dict[str, Any]:
        """Extract detailed document structure information."""
        structure_info = {
            'articles_count': 0,
            'chapters_count': 0,
            'clauses_count': 0,
            'legal_basis_count': 0,
            'signatures_count': 0,
            'issuing_authority': '',
            'has_regulation_section': False,
            'articles_detail': [],
            'legal_basis_detail': [],
            'document_type_detected': '',
            'has_decision_section': False,
            'has_modification_content': False
        }
        
        # Extract articles with detailed content
        articles = self.patterns['article'].findall(text)
        structure_info['articles_count'] = len(articles)
        
        for article_num, article_content in articles:
            # Clean article content
            clean_content = article_content.strip()
            if clean_content:
                structure_info['articles_detail'].append({
                    'number': article_num,
                    'content': clean_content[:200] + '...' if len(clean_content) > 200 else clean_content,
                    'full_content': clean_content
                })
        
        # Count chapters
        chapters = self.patterns['chapter'].findall(text)
        structure_info['chapters_count'] = len(chapters)
        
        # Count clauses
        clauses = self.patterns['clause'].findall(text)
        structure_info['clauses_count'] = len(clauses)
        
        # Extract legal basis with details
        legal_basis = self.patterns['legal_basis'].findall(text)
        structure_info['legal_basis_count'] = len(legal_basis)
        
        for basis in legal_basis:
            clean_basis = basis.strip()
            if clean_basis:
                structure_info['legal_basis_detail'].append(clean_basis)
        
        # Count signatures
        signatures = self.patterns['signature'].findall(text)
        structure_info['signatures_count'] = len(signatures)
        
        # Extract issuing authority
        authority_match = self.patterns['authority'].search(text)
        if authority_match:
            structure_info['issuing_authority'] = authority_match.group(1)
        
        # Detect document type
        doc_type_match = self.patterns['doc_type'].search(text)
        if doc_type_match:
            structure_info['document_type_detected'] = doc_type_match.group(1)
        
        # Check for specific sections
        structure_info['has_regulation_section'] = 'QUY ĐỊNH' in text.upper()
        structure_info['has_decision_section'] = 'QUYẾT ĐỊNH' in text.upper()
        structure_info['has_modification_content'] = any(keyword in text.upper() for keyword in ['SỬA ĐỔI', 'BỔ SUNG', 'THAY THẾ'])
        
        return structure_info
    
    def _create_llm_prompt(self, text: str) -> str:
        """Create prompt for Gemini LLM."""
        # Truncate text if too long
        max_chars = 4000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = f"""Bạn là Document Metadata Agent chuyên phân tích văn bản hành chính Việt Nam.

Phân tích nội dung tiếng Việt từ tài liệu hành chính và trích xuất metadata.

Yêu cầu:
1. Trích các trường JSON sau:
{{
  "doc_id": "",
  "category": "",
  "source": "",
  "date": "",
  "modify": "",
  "partial_mod": false,
  "data_type": "markdown",
  "amend": ""
}}

2. Nếu không có giá trị, để trống.

3. Chọn category theo từ khóa:
   - "Thông tư", "Quy định" → training_and_regulations
   - "Quyết định" → decision
   - "Nghị định", "Chính sách" → policy
   - "Thông báo", "Công văn" → announcement
   - khác → general_document

4. Trích doc_id từ pattern "Số: ..." hoặc số văn bản

5. Trích date từ "ngày ... tháng ... năm ..."

6. Trích source từ tiêu đề chính (dòng có "Về việc", "Ban hành", v.v.)

7. Phân tích modify: nếu có "Sửa đổi", "Bổ sung" thì điền thông tin đó

8. Phân tích amend: nếu có "Bãi bỏ", "Hủy bỏ" thì điền thông tin đó

Nội dung văn bản:
{text}

Trả về JSON hợp lệ:"""
        
        return prompt
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API and return response."""
        try:
            model = genai.GenerativeModel(self.model)
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    response_mime_type="application/json"
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> MetadataResult:
        """Parse LLM response and create MetadataResult."""
        try:
            # Clean response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            # Parse JSON
            data = json.loads(response)
            
            return MetadataResult(
                doc_id=data.get('doc_id', ''),
                category=data.get('category', 'general_document'),
                source=data.get('source', ''),
                date=data.get('date', ''),
                modify=data.get('modify', ''),
                partial_mod=data.get('partial_mod', False),
                data_type=data.get('data_type', 'markdown'),
                amend=data.get('amend', ''),
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
    
    def _merge_results(self, regex_result: MetadataResult, llm_result: MetadataResult, missing_fields: List[str]) -> MetadataResult:
        """Merge regex and LLM results."""
        result_dict = regex_result.to_dict()
        llm_dict = llm_result.to_dict()
        
        # Fill missing fields with LLM results
        for field in missing_fields:
            if llm_dict.get(field):
                result_dict[field] = llm_dict[field]
        
        return MetadataResult(**result_dict)
    
    def _create_empty_result(self) -> MetadataResult:
        """Create empty metadata result."""
        return MetadataResult(
            doc_id="",
            category="general_document",
            source="",
            date="",
            modify="",
            partial_mod=False,
            data_type="markdown",
            amend="",
        )
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        # Use first 200 chars + hash for key
        text_sample = text[:200]
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"metadata:{text_hash}:{hashlib.md5(text_sample.encode()).hexdigest()}"
    
    def _get_from_cache(self, text: str) -> Optional[MetadataResult]:
        """Get metadata from cache."""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(text)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                # Ensure cached_data is a string before parsing JSON
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                elif not isinstance(cached_data, str):
                    # Handle other types by converting to string
                    cached_data = str(cached_data)
                data = json.loads(cached_data)
                return MetadataResult(**data)
            
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        
        return None
    
    def _save_to_cache(self, text: str, result: MetadataResult) -> None:
        """Save metadata to cache."""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(text)
            data = json.dumps(result.to_dict())
            self.redis_client.setex(cache_key, self.cache_ttl, data)
            
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")


def analyze_document(text: str, config: Optional[Dict[str, Any]] = None, mode: str = 'hybrid') -> Dict[str, Any]:
    """
    Convenience function to analyze document metadata.
    
    Args:
        text: Document text content
        config: Optional configuration dictionary
        mode: Extraction mode ('regex', 'llm', 'hybrid')
        
    Returns:
        Dictionary with metadata
    """
    agent = MetadataAgent(config)
    result = agent.analyze_document(text, mode)
    return result.to_dict()
