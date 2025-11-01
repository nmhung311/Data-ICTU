# Notebook Application

Ứng dụng Notebook với khả năng upload PDF, trích xuất text và chat với nội dung PDF.

## Cấu trúc dự án

```
data-md/
├── frontend/     # React + TypeScript + Vite
└── backend/      # Flask API (Python)
```

## Chạy ứng dụng

### 1. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend sẽ chạy tại: http://localhost:5173

### 2. Backend

Trước tiên, cài đặt pip (nếu chưa có):

```bash
sudo apt install python3-pip
```

Sau đó cài dependencies và chạy backend:

```bash
cd backend
python3 -m pip install --user Flask flask-cors pdfplumber PyPDF2
python3 app.py
```

Backend sẽ chạy tại: http://localhost:5000

## Tính năng

- ✅ Upload file PDF
- ✅ Trích xuất text từ PDF sang Markdown
- ✅ Chat với nội dung PDF (gửi câu hỏi và nhận câu trả lời)
- ✅ Xem PDF trực tiếp trong ứng dụng
- ✅ Quản lý nguồn (đổi tên, xóa, chọn)

## API Endpoints

Xem chi tiết trong `/backend/README.md`





