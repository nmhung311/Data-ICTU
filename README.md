# 📚 Data-MD Application

Ứng dụng Notebook với khả năng upload PDF, trích xuất text và chat với nội dung PDF.

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?style=flat-square&logo=github)](https://github.com/nmhung311/Process-Data-chatbot-ICTU)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

## Cấu trúc dự án

```
data-md/
├── frontend/     # React + TypeScript + Vite
└── backend/      # Flask API (Python)
```

## 🛠️ Cài đặt và Chạy ứng dụng

### Cách 1: Sử dụng Docker (Khuyến nghị)

1. **Clone repository:**
   ```bash
   git clone https://github.com/nmhung311/Process-Data-chatbot-ICTU.git
   cd Process-Data-chatbot-ICTU
   ```

2. **Tạo file `.env` trong thư mục gốc:**
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Chạy với Docker Compose:**
   ```bash
   docker compose up -d
   ```

4. **Truy cập ứng dụng:**
   - Frontend: http://localhost:8080
   - Backend API: http://localhost:5000

5. **Xem logs:**
   ```bash
   docker compose logs -f
   ```

6. **Dừng ứng dụng:**
   ```bash
   docker compose down
   ```

### Cách 2: Chạy thủ công (Development)

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend sẽ chạy tại: http://localhost:5173

#### Backend

1. **Cài đặt dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Chạy backend:**
   ```bash
   python3 app.py
   ```

Backend sẽ chạy tại: http://localhost:5000

## 🚀 Tính năng

- ✅ Upload file PDF, DOCX, TXT, MD
- ✅ Trích xuất text từ PDF với OCR hỗ trợ
- ✅ Preview file PDF, TXT, Markdown trực tiếp trong ứng dụng
- ✅ Chat với nội dung PDF (gửi câu hỏi và nhận câu trả lời)
- ✅ Tạo metadata tự động từ document (với OpenAI API)
- ✅ Quản lý nguồn (đổi tên, xóa, chọn)
- ✅ Docker containerization hỗ trợ

## 📸 Preview

![Application Preview](https://via.placeholder.com/800x400/4F46E5/FFFFFF?text=Data-MD+Application+Preview)

> 💡 **Lưu ý**: Thay thế URL trên bằng screenshot thực tế của ứng dụng.

## 📡 API Endpoints

- `POST /api/upload-pdf` - Upload file PDF/DOCX/TXT/MD
- `POST /api/extract-pdf` - Trích xuất text từ PDF
- `POST /api/generate-metadata` - Tạo metadata từ document
- `GET /api/documents` - Lấy danh sách documents
- `GET /api/documents/<id>` - Lấy thông tin document
- `POST /api/chat` - Chat với nội dung PDF
- `GET /api/health` - Health check

Xem chi tiết trong `/backend/README.md`

## 🔗 Links

- **Repository**: [GitHub](https://github.com/nmhung311/Process-Data-chatbot-ICTU)
- **Issues**: [Report Bug](https://github.com/nmhung311/Process-Data-chatbot-ICTU/issues)

## 📝 License

MIT License - xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## 👥 Contributors

- [nmhung311](https://github.com/nmhung311)





