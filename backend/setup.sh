#!/bin/bash

# Script để cài đặt và chạy Flask backend

echo "📦 Đang kiểm tra Python và pip..."

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 chưa được cài đặt. Vui lòng cài đặt Python3 trước."
    exit 1
fi

# Thử cài pip nếu chưa có
if ! python3 -m pip --version &> /dev/null; then
    echo "📥 Đang cài đặt pip..."
    python3 -m ensurepip --upgrade || {
        echo "⚠️  Không thể tự động cài pip. Vui lòng chạy:"
        echo "   sudo apt install python3-pip"
        exit 1
    }
fi

# Cài đặt dependencies
echo "📦 Đang cài đặt dependencies..."
python3 -m pip install --user Flask flask-cors pdfplumber PyPDF2

echo "✅ Đã cài đặt xong!"
echo "🚀 Để chạy backend: python3 app.py"





