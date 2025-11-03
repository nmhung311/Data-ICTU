# Dockerfile cho Flask Backend
FROM python:3.11-slim

# Cài đặt system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-vie \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Thiết lập working directory
WORKDIR /app

# Copy requirements và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cài đặt thêm python-docx cho DOCX support
RUN pip install --no-cache-dir python-docx

# Copy toàn bộ code của backend
COPY . .

# Tạo thư mục uploads nếu chưa có
RUN mkdir -p uploads

# Set environment variables cho Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port 5000
EXPOSE 5000

# Chạy Flask app
CMD ["python", "app.py"]

