#!/bin/bash
# Script để lấy IP local và tạo link chia sẻ

echo "🌐 Đang lấy thông tin mạng..."

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    IP=$(hostname -I | awk '{print $1}')
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Mac
    IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1)
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash)
    IP=$(ipconfig | grep "IPv4" | head -1 | awk '{print $NF}')
else
    IP="YOUR_IP_HERE"
fi

if [ -z "$IP" ]; then
    echo "❌ Không thể lấy IP tự động"
    echo "📝 Vui lòng tìm IP thủ công:"
    echo "   Linux/Mac: ip addr show hoặc ifconfig"
    echo "   Windows: ipconfig"
    exit 1
fi

echo ""
echo "✅ IP của bạn: $IP"
echo ""
echo "🔗 Link chia sẻ trong mạng LAN:"
echo "   http://$IP:8080"
echo ""
echo "📋 Để người khác truy cập:"
echo "   1. Đảm bảo họ cùng mạng WiFi/Network với bạn"
echo "   2. Gửi họ link: http://$IP:8080"
echo ""
echo "🔒 Nếu không truy cập được, kiểm tra firewall:"
echo "   sudo ufw allow 8080/tcp"
echo "   sudo ufw allow 5000/tcp"

