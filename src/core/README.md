# Document Splitter

Enhanced Vietnamese Legal Document Splitter với LLM integration.

## Tính năng

- Chia văn bản theo cấu trúc pháp lý Việt Nam
- Phân loại tự động bằng Gemini AI
- Xử lý pattern đặc biệt ("như sau:", "Quy trình")
- Metadata chuẩn hóa 8 trường

## Sử dụng

```python
from src.core.document_splitter import split_vietnamese_legal_document

# Chia văn bản thành blocks
result = split_vietnamese_legal_document(text, api_key="your_gemini_key")
```

## Cấu trúc output

Mỗi block chứa:
- **Metadata**: 8 trường chuẩn
- **Content**: Nội dung gốc không chỉnh sửa
