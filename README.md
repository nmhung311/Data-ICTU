# Validate Data System

Hệ thống xử lý và phân tích văn bản pháp lý Việt Nam với AI.

## 🏗️ Cấu trúc dự án

```
validate-data-system/
├── 📁 src/                          # Source code chính
│   ├── 📁 api/                      # API endpoints
│   │   └── app.py                   # Flask app chính
│   ├── 📁 core/                     # Core business logic
│   │   ├── document_splitter.py     # Enhanced VN Legal Splitter
│   │   └── category_classifier.py   # Category classification
│   ├── 📁 models/                   # Data models
│   └── 📁 utils/                    # Utilities
│       ├── config.py               # Configuration
│       ├── database.py            # Database operations
│       └── helpers.py              # Helper functions
├── 📁 config/                       # Configuration files
├── 📁 data/                        # Data storage
│   ├── 📁 uploads/                # Uploaded files
│   ├── 📁 outputs/                # Processed outputs
│   └── 📁 temp/                    # Temporary files
├── 📁 logs/                        # Log files
├── 📁 tests/                       # Test files
├── 📁 docs/                        # Documentation
├── 📁 deployment/                  # Deployment configs
└── 📁 raw2md_agent/               # Raw2MD Agent
```

## 🚀 Tính năng chính

- **Document Splitting**: Chia văn bản pháp lý theo cấu trúc phân tầng Việt Nam
- **AI Classification**: Phân loại tự động bằng LLM (Gemini)
- **OCR Processing**: Xử lý hình ảnh và PDF scan
- **Metadata Extraction**: Trích xuất metadata chuẩn hóa
- **REST API**: API endpoints cho tích hợp

## 📋 Yêu cầu hệ thống

- Python 3.8+
- Flask
- Google Generative AI (Gemini)
- Tesseract OCR

## 🛠️ Cài đặt

```bash
pip install -r requirements.txt
```

## 🏃‍♂️ Chạy ứng dụng

```bash
python src/api/app.py
```

## 📚 Documentation

- [API Documentation](docs/api/)
- [User Guide](docs/user-guide/)
- [Deployment Guide](deployment/)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

MIT License