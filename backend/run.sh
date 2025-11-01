#!/bin/bash

# Script để chạy Flask backend

cd "$(dirname "$0")"

# Kiểm tra virtual environment
if [ ! -d "venv" ]; then
    echo "Đang tạo virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Cài đặt dependencies nếu chưa có
if [ ! -f "venv/bin/flask" ]; then
    echo "Đang cài đặt dependencies..."
    pip install -r requirements.txt
fi

# Chạy Flask app
echo "🚀 Đang khởi động Flask backend..."
python app.py





