# Raw2MD Agent - Metadata Processing System

## 📋 Tổng quan

Raw2MD Agent là một hệ thống xử lý tài liệu pháp lý Việt Nam với khả năng tự động chia tài liệu thành các metadata blocks và hiển thị chúng dưới dạng cards trực quan.

## ✨ Tính năng chính

### 🔧 Backend (Flask API)
- **Document Processing**: Xử lý đa định dạng (PDF, DOCX, TXT, HTML, CSV, XML)
- **Metadata Extraction**: Tự động trích xuất metadata từ văn bản pháp lý
- **Category Classification**: Phân loại tự động bằng LLM (Gemini 2.5 Flash)
- **Database Management**: SQLite với metadata blocks storage
- **File Management**: Upload, rename, delete, view files

### 🎨 Frontend (React)
- **Modern UI**: Giao diện hiện đại với sidebar resizable
- **Metadata Cards**: Hiển thị metadata blocks dưới dạng cards
- **File Upload**: Upload đơn/multiple files với progress indicator
- **Document Viewer**: Xem tài liệu PDF trực tiếp trong browser
- **Responsive Design**: Tương thích với mọi kích thước màn hình

### 🧠 Core Modules
- **Document Splitter**: Chia văn bản pháp lý thành Điều/Khoản/Điểm
- **Category Classifier**: Phân loại category từ tên file
- **LLM Service**: Tích hợp Gemini API cho xử lý ngôn ngữ tự nhiên

## 🚀 Cài đặt và Chạy

### Yêu cầu hệ thống
- Python 3.8+
- Node.js 16+ (cho frontend development)
- Git

### Backend Setup
```bash
cd web-app/backend
pip install -r requirements.txt
python app.py
```

### Frontend Setup
```bash
cd web-app/frontend
# Mở index.html trong browser hoặc serve với HTTP server
python -m http.server 3000
```

### Docker Setup
```bash
cd web-app/backend
docker-compose up -d
```

## 📁 Cấu trúc dự án

```
Validate Data/
├── .gitignore                 # Git ignore rules
├── README.md                  # Documentation chính
├── requirements.txt           # Python dependencies
├── docs/                     # Documentation
│   ├── api/README.md
│   └── user-guide/README.md
├── src/                      # Source code modules
│   ├── api/README.md
│   └── core/README.md
└── web-app/                  # Web application
    ├── README.md
    ├── backend/              # Flask API
    │   ├── src/
    │   │   ├── api/         # API routes
    │   │   ├── core/        # Core modules
    │   │   ├── models/      # Data models
    │   │   └── utils/       # Utilities
    │   ├── raw2md_agent/    # Legacy modules
    │   ├── deployment/      # Docker & K8s configs
    │   ├── requirements.txt
    │   └── app.py          # Main Flask app
    └── frontend/           # React frontend
        ├── app.js         # Main React app
        ├── styles.css     # CSS styles
        ├── index.html     # HTML template
        └── package.json   # Frontend dependencies
```

## 🔌 API Endpoints

### File Management
- `POST /api/sources` - Upload file
- `GET /api/sources` - List all sources
- `GET /api/sources/{id}/info` - Get source info
- `GET /api/sources/{id}/content` - Get source content
- `PUT /api/sources/{id}` - Rename source
- `DELETE /api/sources/{id}` - Delete source

### Metadata Processing
- `GET /api/metadata` - Get all metadata blocks
- `POST /api/sources/{id}/process-metadata` - Process file to metadata
- `GET /api/metadata/{id}` - Get specific metadata block
- `DELETE /api/metadata/{id}` - Delete metadata block

### System
- `GET /api/health` - Health check
- `GET /api/config` - System configuration
- `GET /api/stats` - System statistics

## 🎯 Workflow

1. **Upload File** → User uploads document
2. **Auto Processing** → System automatically processes metadata
3. **Document Splitting** → Core modules split document into blocks
4. **Metadata Extraction** → Extract metadata for each block
5. **Database Storage** → Save blocks to SQLite database
6. **UI Display** → Frontend displays metadata blocks as cards

## 🛠️ Công nghệ sử dụng

### Backend
- **Flask**: Web framework
- **SQLite**: Database
- **Google Gemini**: LLM service
- **Pydantic**: Data validation
- **Werkzeug**: WSGI utilities

### Frontend
- **React**: UI framework
- **Vanilla CSS**: Styling
- **Fetch API**: HTTP requests
- **SVG Icons**: UI icons

### Core Processing
- **Document Splitter**: Vietnamese legal document parsing
- **Category Classifier**: File-based categorization
- **LLM Integration**: AI-powered metadata extraction

## 📊 Database Schema

### Sources Table
- `id`, `filename`, `file_path`, `file_type`, `file_size`, `created_at`

### Metadata Blocks Table
- `id`, `doc_id`, `data_type`, `category`, `date`, `source`, `content`, `confidence`, `created_at`

## 🔧 Configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key
- `GEMINI_API_KEY`: Google Gemini API key
- `MAX_FILE_SIZE_MB`: Maximum file upload size
- `OCR_ENABLED`: Enable OCR processing

### Config File
- `web-app/backend/src/utils/config.py`: Main configuration

## 🚀 Deployment

### Docker
```bash
cd web-app/backend
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f web-app/backend/deployment/k8s/raw2md-agent.yaml
```

## 📝 Development

### Adding New Features
1. Backend: Add routes in `src/utils/routes.py`
2. Frontend: Update `app.js` and `styles.css`
3. Core: Extend modules in `src/core/`

### Testing
- Backend: Use Flask test client
- Frontend: Manual testing in browser
- Integration: Test full workflow

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Create GitHub issue
- Check documentation in `docs/`
- Review API endpoints in `docs/api/`

---

**Raw2MD Agent** - Transforming legal documents into structured metadata blocks! 🎉