# Hướng Dẫn Push Dự Án Lên GitHub Repository

## 📋 Repository: Process-Data-chatbot-ICTU

## Bước 1: Kiểm Tra Git Status

```powershell
cd "D:\Validate Data"
git status
```

## Bước 2: Thêm Remote Repository (Nếu chưa có)

```powershell
# Xem remote hiện tại
git remote -v

# Nếu chưa có remote, thêm mới:
git remote add origin https://github.com/YOUR_USERNAME/Process-Data-chatbot-ICTU.git

# Hoặc nếu muốn đổi remote hiện tại:
git remote set-url origin https://github.com/YOUR_USERNAME/Process-Data-chatbot-ICTU.git
```

## Bước 3: Thêm Tất Cả Files

```powershell
# Thêm tất cả files đã thay đổi
git add .

# Hoặc thêm từng file cụ thể
git add web-app/
git add README.md
git add .gitignore
```

## Bước 4: Commit Changes

```powershell
git commit -m "Initial commit: Vietnamese Legal Document Metadata Extractor with OpenAI GPT-4o integration"
```

## Bước 5: Push Lên GitHub

### Lần đầu tiên (chưa có branch trên remote):

```powershell
# Push và set upstream
git push -u origin main

# Hoặc nếu branch của bạn là master:
git push -u origin master
```

### Các lần sau:

```powershell
git push
```

## 🔒 Lưu Ý Quan Trọng

### 1. Kiểm Tra `.gitignore`

Đảm bảo các file nhạy cảm đã được ignore:
- `.env` (chứa API keys)
- `*.db`, `*.sqlite` (database files)
- `web-app/data/uploads/`, `web-app/data/outputs/` (user data)
- `logs/`, `*.log` (log files)
- `__pycache__/`, `*.pyc` (Python cache)

### 2. Tạo File `.env.example`

Tạo file `.env.example` để hướng dẫn setup (không chứa API key thật):

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# OCR Configuration
OCR_ENABLED=true
TESSERACT_PATH=/usr/bin/tesseract
OCR_LANG=vie+eng

# File Upload Configuration
MAX_FILE_SIZE_MB=100
```

### 3. Không Commit API Keys

**⚠️ QUAN TRỌNG**: KHÔNG commit file `.env` chứa API keys thật!

Kiểm tra trước khi commit:
```powershell
git status
# Xem file nào sẽ được commit
# Đảm bảo .env KHÔNG có trong danh sách
```

## 📝 Workflow Hoàn Chỉnh

```powershell
# 1. Check status
cd "D:\Validate Data"
git status

# 2. Add files
git add .

# 3. Check lại (xem file nào sẽ commit)
git status

# 4. Commit
git commit -m "Your commit message"

# 5. Push
git push -u origin main
```

## 🔍 Troubleshooting

### Lỗi: "remote origin already exists"

```powershell
# Xóa remote cũ
git remote remove origin

# Thêm lại
git remote add origin https://github.com/YOUR_USERNAME/Process-Data-chatbot-ICTU.git
```

### Lỗi: "Authentication failed"

Sử dụng Personal Access Token thay vì password:
1. GitHub Settings → Developer settings → Personal access tokens
2. Tạo token mới với quyền `repo`
3. Dùng token thay vì password khi push

### Lỗi: "Failed to push some refs"

```powershell
# Pull changes từ remote trước
git pull origin main --rebase

# Sau đó push lại
git push
```

### Conflict với remote

```powershell
# Pull và merge
git pull origin main

# Resolve conflicts nếu có, sau đó:
git add .
git commit -m "Merge remote changes"
git push
```

## 📚 Tài Liệu Tham Khảo

- GitHub Docs: https://docs.github.com/en/get-started
- Git Basics: https://git-scm.com/book/en/v2/Getting-Started-Git-Basics

