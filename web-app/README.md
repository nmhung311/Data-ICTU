# Raw2MD Agent Web Application

Web interface cho Raw2MD Agent với React frontend và Flask backend, tích hợp đầy đủ với các folder hiện có.

## 🚀 Quick Start

### Development Mode
```bash
# Khởi động ứng dụng web
python start.py
```

### Production Mode với Docker
```bash
# Build và khởi động với Docker Compose
docker-compose up --build
```

## 📁 Cấu trúc

```
web-app/
├── backend/                 # Flask API server
│   ├── app.py              # Main API application
│   ├── config/             # Configuration files
│   │   ├── settings.py     # Backend configuration
│   │   └── README.md       # Config documentation
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile         # Docker configuration
├── frontend/               # React frontend
│   ├── index.html         # React app
│   └── package.json       # Frontend dependencies
├── docker-compose.yml     # Docker Compose configuration
└── start.py              # Development launcher
```

## 🔧 API Endpoints

### Core Endpoints
- `GET /api/health` - Health check với thông tin hệ thống
- `GET /api/supported-formats` - Supported file formats
- `POST /api/process` - Process document
- `GET /api/result/<id>` - Get result
- `GET /api/download/<id>` - Download markdown

### Management Endpoints
- `GET /api/files` - List uploaded files
- `GET /api/results` - List processing results
- `GET /api/config` - Get system configuration
- `GET /api/ocr-status` - OCR status

## 📋 Supported Formats

- **Documents**: PDF, DOCX, HTML, TXT, CSV, XML, JSON
- **Images**: JPG, PNG, TIFF, BMP, WebP

## ✨ Features

### Core Features
- 📁 Drag & drop file upload
- 🔍 OCR với PaddleOCR
- 🤖 AI metadata extraction
- 📝 Markdown conversion
- 📥 Download results
- 📋 Copy to clipboard

### Advanced Features
- 🔄 Advanced processing pipeline
- 📊 Processing statistics
- 📁 File management
- 🔍 Result history
- 📈 System monitoring
- 🐳 Docker support
- ☸️ Kubernetes ready

## 🛠️ Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend Development
```bash
cd frontend
python -m http.server 3000
```

### Full Stack Development
```bash
python start.py
```

## 🐳 Docker Deployment

### Build và Run
```bash
# Build backend
cd backend
docker build -t raw2md-agent-backend .

# Run với Docker Compose
docker-compose up --build
```

### Services
- **Backend**: http://localhost:5000
- **Frontend**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Redis**: localhost:6379

## ☸️ Kubernetes Deployment

### Deploy với kubectl
```bash
# Apply Kubernetes manifests
kubectl apply -f ../k8s/raw2md-agent.yaml

# Check deployment
kubectl get pods -n raw2md-agent
kubectl get services -n raw2md-agent
```

### Monitoring
```bash
# Port forward Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

## 📊 Monitoring

### Metrics
- Processing requests count
- Processing time
- File upload size
- Error rates
- OCR usage

### Logs
- Application logs: `raw2md_api.log`
- Processing logs với structured logging
- Error tracking và debugging

## 🔧 Configuration

### Environment Variables
```bash
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key

# Raw2MD Agent Configuration
RAWM2D_AGENT_ENABLED=True
OCR_ENABLED=True
METADATA_EXTRACTION_ENABLED=True

# File Upload Configuration
MAX_FILE_SIZE_MB=100
UPLOAD_FOLDER=../uploads
OUTPUT_FOLDER=../outputs
```

### Folder Integration
- **uploads/**: File upload storage
- **outputs/**: Processing results
- **k8s/**: Kubernetes manifests
- **monitoring/**: Prometheus configuration
- **raw2md_agent/**: Core library

## 🚀 Production Deployment

### Requirements
- Python 3.11+
- Docker & Docker Compose
- Kubernetes cluster (optional)
- Redis (for caching)
- Prometheus (for monitoring)

### Performance
- Multi-worker Gunicorn
- Redis caching
- File streaming
- Async processing
- Health checks

## 📝 API Documentation

### Process Document
```bash
curl -X POST http://localhost:5000/api/process \
  -F "file=@document.pdf" \
  -F "ocr_enabled=true" \
  -F "extract_metadata=false"
```

### Get Result
```bash
curl http://localhost:5000/api/result/{result_id}
```

### Download Markdown
```bash
curl -O http://localhost:5000/api/download/{result_id}
```

## 🔍 Troubleshooting

### Common Issues
1. **OCR not working**: Check PaddleOCR installation
2. **File upload fails**: Check file size limits
3. **Processing errors**: Check logs in `raw2md_api.log`
4. **Docker issues**: Check Docker logs

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python app.py
```

## 📈 Performance Optimization

### Backend
- Use Gunicorn with multiple workers
- Enable Redis caching
- Optimize file processing
- Use async processing for large files

### Frontend
- Minify JavaScript và CSS
- Use CDN for static assets
- Implement lazy loading
- Optimize images

## 🔒 Security

### Best Practices
- Input validation
- File type checking
- Size limits
- CORS configuration
- Secret key management
- HTTPS in production

## 📞 Support

- **Documentation**: Check README files
- **Issues**: Create GitHub issues
- **Logs**: Check `raw2md_api.log`
- **Health**: Use `/api/health` endpoint
