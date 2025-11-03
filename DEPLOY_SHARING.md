# 🌐 Hướng dẫn Chia sẻ Link cho Người khác

Có nhiều cách để chia sẻ ứng dụng của bạn cho người khác truy cập:

## 📋 Mục lục

1. [Cách 1: Chia sẻ trong mạng LAN (Miễn phí, Nhanh)](#cách-1-chia-sẻ-trong-mạng-lan)
2. [Cách 2: Ngrok (Miễn phí, Dễ dùng)](#cách-2-ngrok)
3. [Cách 3: Cloudflare Tunnel (Miễn phí, Tốt nhất)](#cách-3-cloudflare-tunnel)
4. [Cách 4: Deploy lên VPS/Cloud Server](#cách-4-deploy-lên-vpscloud-server)
5. [Cách 5: Railway/Render/Fly.io (Platform as a Service)](#cách-5-platform-as-a-service)

---

## Cách 1: Chia sẻ trong mạng LAN

**Ưu điểm:** Miễn phí, nhanh, không cần cài thêm  
**Nhược điểm:** Chỉ trong cùng mạng WiFi/Network

### Bước 1: Tìm IP của máy bạn

**Linux/Mac:**
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
# Hoặc
hostname -I
```

**Windows:**
```cmd
ipconfig
# Tìm "IPv4 Address" (ví dụ: 192.168.1.100)
```

### Bước 2: Đảm bảo ứng dụng bind với 0.0.0.0

Kiểm tra `docker-compose.yml` - đã đúng rồi vì backend đã có `host='0.0.0.0'`.

### Bước 3: Chia sẻ link

Link sẽ là: `http://YOUR_IP:8080`

**Ví dụ:** Nếu IP của bạn là `192.168.1.100`, link sẽ là:
```
http://192.168.1.100:8080
```

### Bước 4: Mở firewall (nếu cần)

**Linux (UFW):**
```bash
sudo ufw allow 8080/tcp
sudo ufw allow 5000/tcp
```

**Linux (Firewalld):**
```bash
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```

---

## Cách 2: Ngrok

**Ưu điểm:** Miễn phí, dễ dùng, có subdomain tùy chỉnh (paid)  
**Nhược điểm:** Link thay đổi mỗi lần restart (free), giới hạn băng thông

### Bước 1: Cài đặt Ngrok

**Linux:**
```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

Hoặc download từ: https://ngrok.com/download

### Bước 2: Đăng ký và lấy auth token

1. Đăng ký tại: https://dashboard.ngrok.com/signup
2. Copy auth token từ dashboard
3. Chạy: `ngrok config add-authtoken YOUR_TOKEN`

### Bước 3: Chạy Ngrok

```bash
ngrok http 8080
```

Bạn sẽ nhận được link dạng: `https://xxxx-xx-xx-xx-xx.ngrok-free.app`

### Bước 4: Cập nhật docker-compose cho Ngrok

Nếu muốn chạy Ngrok trong Docker, tạo file `docker-compose.ngrok.yml`:

```yaml
services:
  ngrok:
    image: ngrok/ngrok:latest
    command: http data-md-frontend:80
    networks:
      - data-md-network
    depends_on:
      - frontend
```

---

## Cách 3: Cloudflare Tunnel

**Ưu điểm:** Miễn phí, link cố định, không giới hạn băng thông, bảo mật tốt  
**Nhược điểm:** Cần đăng ký Cloudflare

### Bước 1: Cài đặt Cloudflared

**Linux:**
```bash
# Download và cài đặt
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### Bước 2: Đăng nhập Cloudflare

```bash
cloudflared tunnel login
```

### Bước 3: Tạo tunnel

```bash
cloudflared tunnel create data-md-tunnel
```

### Bước 4: Tạo config file

Tạo file `~/.cloudflared/config.yml`:
```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/YOUR_USER/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: your-domain.workers.dev
    service: http://localhost:8080
  - service: http_status:404
```

### Bước 5: Chạy tunnel

```bash
cloudflared tunnel run data-md-tunnel
```

---

## Cách 4: Deploy lên VPS/Cloud Server

**Ưu điểm:** Link cố định, kiểm soát hoàn toàn, có thể dùng domain  
**Nhược điểm:** Tốn phí (nhưng rẻ), cần kiến thức server

### Bước 1: Chọn VPS

- **DigitalOcean:** $6/tháng (1GB RAM)
- **Linode:** $5/tháng
- **Vultr:** $2.50/tháng (1GB RAM)
- **Hetzner:** €4/tháng (rất rẻ ở EU)
- **AWS EC2:** Free tier 1 năm đầu

### Bước 2: Setup Server

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Cài Docker Compose
sudo apt install docker-compose-plugin -y

# Clone repo
git clone YOUR_REPO_URL
cd data-md
```

### Bước 3: Setup Domain (Optional)

1. Mua domain (Namecheap, GoDaddy, v.v.)
2. Point A record về IP của VPS
3. Setup SSL với Let's Encrypt (Certbot)

### Bước 4: Chạy với Docker

```bash
# Tạo .env file
echo "OPENAI_API_KEY=your_key" > .env

# Chạy
docker compose up -d
```

### Bước 5: Setup Nginx Reverse Proxy (Cho domain)

Tạo `/etc/nginx/sites-available/data-md`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable và reload:
```bash
sudo ln -s /etc/nginx/sites-available/data-md /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Cách 5: Platform as a Service

**Ưu điểm:** Dễ deploy, tự động SSL, không cần quản lý server  
**Nhược điểm:** Có thể tốn phí, giới hạn tài nguyên

### Railway

1. Đăng ký tại: https://railway.app
2. Connect GitHub repo
3. Deploy từ `docker-compose.yml`
4. Link tự động: `your-app.railway.app`

### Render

1. Đăng ký tại: https://render.com
2. Tạo Web Service từ Docker
3. Deploy
4. Link tự động: `your-app.onrender.com`

### Fly.io

1. Đăng ký tại: https://fly.io
2. Cài CLI: `curl -L https://fly.io/install.sh | sh`
3. Deploy: `flyctl launch`

---

## 📝 So sánh nhanh

| Cách | Chi phí | Khó | Link cố định | Tốc độ | Bảo mật |
|------|---------|-----|--------------|--------|---------|
| LAN | Miễn phí | ⭐ | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Ngrok | Miễn phí | ⭐ | ❌ (Free) | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Cloudflare | Miễn phí | ⭐⭐ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| VPS | $2-10/tháng | ⭐⭐⭐ | ✅ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| PaaS | Free-$5/tháng | ⭐⭐ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🚀 Khuyến nghị

- **Test nhanh:** Dùng Ngrok hoặc LAN
- **Chia sẻ lâu dài:** Cloudflare Tunnel (miễn phí) hoặc VPS
- **Production:** VPS + Domain + SSL

---

## 🔐 Lưu ý bảo mật

1. **Đặt mật khẩu cho ứng dụng** (nếu có)
2. **Giới hạn IP truy cập** (nếu dùng VPS)
3. **Dùng HTTPS** (SSL/TLS)
4. **Bảo vệ API key** - không commit vào Git
5. **Rate limiting** cho API endpoints

---

## 📞 Cần hỗ trợ?

Nếu gặp vấn đề, hãy kiểm tra:
- Firewall đã mở port chưa?
- Docker containers đang chạy chưa?
- Logs: `docker compose logs`
- Network: `docker compose ps`

