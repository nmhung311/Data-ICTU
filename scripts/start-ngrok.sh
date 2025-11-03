#!/bin/bash
# Script để chạy Ngrok cho ứng dụng

echo "🚀 Đang khởi động Ngrok..."

# Kiểm tra Ngrok đã cài chưa
if ! command -v ngrok &> /dev/null
then
    echo "❌ Ngrok chưa được cài đặt!"
    echo "📥 Đang cài đặt Ngrok..."
    
    # Linux
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
        sudo apt update && sudo apt install ngrok -y
    # Mac
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ngrok/ngrok/ngrok
    else
        echo "⚠️ Vui lòng cài Ngrok thủ công từ https://ngrok.com/download"
        exit 1
    fi
fi

# Kiểm tra đã có auth token chưa
if [ ! -f ~/.ngrok2/ngrok.yml ]; then
    echo "⚠️ Chưa có auth token!"
    echo "📝 Vui lòng:"
    echo "   1. Đăng ký tại https://dashboard.ngrok.com/signup"
    echo "   2. Copy auth token"
    echo "   3. Chạy: ngrok config add-authtoken YOUR_TOKEN"
    exit 1
fi

# Kiểm tra Docker containers đang chạy chưa
if ! docker ps | grep -q "data-md-frontend"; then
    echo "⚠️ Docker containers chưa chạy!"
    echo "🚀 Đang khởi động Docker containers..."
    docker compose up -d
    sleep 5
fi

# Chạy Ngrok
echo "✅ Đang tạo tunnel..."
echo "📱 Link sẽ hiển thị ở đây:"
echo ""
ngrok http 8080

