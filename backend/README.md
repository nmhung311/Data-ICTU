# Backend API cho Notebook

## Yêu cầu

- Python 3.7+
- pip (Python package manager)

## Cài đặt

### Bước 1: Cài đặt pip (nếu chưa có)

```bash
sudo apt install python3-pip
```

### Bước 2: Cài đặt dependencies

```bash
cd /home/namper/Documents/data-md/backend
python3 -m pip install --user Flask flask-cors pdfplumber PyPDF2
```

Hoặc nếu bạn muốn cài global (cần sudo):

```bash
sudo python3 -m pip install Flask flask-cors pdfplumber PyPDF2
```

## Chạy Backend

```bash
python3 app.py
```

Backend sẽ chạy tại: http://localhost:5000

## API Endpoints

### POST /api/upload-pdf
Upload file PDF và trích xuất text sang markdown.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (PDF file)

**Response:**
```json
{
  "filepath": "uploads/20241201_123456_document.pdf",
  "markdown": "# Nội dung markdown..."
}
```

### POST /api/chat
Gửi câu hỏi và nhận câu trả lời dựa trên PDF đã upload.

**Request:**
```json
{
  "question": "Câu hỏi của bạn",
  "filepath": "uploads/20241201_123456_document.pdf"
}
```

**Response:**
```json
{
  "answer": "Câu trả lời...",
  "markdown": "# Nội dung markdown liên quan..."
}
```

## Lưu ý

- File PDF được lưu trong thư mục `uploads/`
- Markdown được tạo tự động khi upload PDF
- Đảm bảo frontend đang chạy ở http://localhost:5173 (hoặc port tương ứng)
