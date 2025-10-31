#!/bin/bash
# Start frontend web server on IP address để người khác có thể truy cập
# Usage: ./start-server.sh [port]
# Default port: 8080

PORT=${1:-8080}

echo "========================================"
echo "Starting Frontend Server"
echo "========================================"
echo ""
echo "Server will be accessible at:"
echo "  - http://localhost:${PORT}"
echo "  - http://YOUR_IP_ADDRESS:${PORT}"
echo ""
echo "To find your IP address, run: ipconfig (Windows) or ifconfig (Linux/Mac)"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

cd "$(dirname "$0")"
python3 -m http.server ${PORT} --bind 0.0.0.0

