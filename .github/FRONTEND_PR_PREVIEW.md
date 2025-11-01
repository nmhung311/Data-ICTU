# 🔧 Hướng dẫn Fix Frontend PR Preview

## Vấn đề

Frontend trong PR Preview không hoạt động vì:
- Frontend được deploy lên GitHub Pages (public)
- Backend vẫn chạy ở `localhost:5000` (local, không public)
- Frontend không thể kết nối được với backend

## ✅ Đã sửa

1. **Tạo API config**: `frontend/src/config/api.ts`
   - Sử dụng `import.meta.env.VITE_API_URL` thay vì hardcode
   - Fallback về `localhost:5000` cho development

2. **Cập nhật tất cả API calls**:
   - `Index.tsx`: Sử dụng `API_BASE_URL` từ config
   - `StudioColumn.tsx`: Sử dụng env var cho extract API
   - `TextPreviewContent.tsx`: Sử dụng env var cho file fetch
   - `ConversationColumn.tsx`: Sử dụng env var cho messages API

## 🔧 Giải pháp để Frontend PR Preview hoạt động

### Cách 1: Deploy Backend Public (Khuyến nghị)

Deploy backend lên một service public:
- **Railway**: https://railway.app
- **Render**: https://render.com
- **Heroku**: https://heroku.com
- **Fly.io**: https://fly.io
- **DigitalOcean App Platform**: https://www.digitalocean.com/products/app-platform

Sau đó:
1. Vào: Repository → Settings → Secrets and variables → Actions
2. Thêm Secret: `VITE_API_URL`
3. Giá trị: `https://your-backend-url.com` (không có trailing slash)
4. Workflow sẽ tự động dùng secret này khi build

### Cách 2: Sử dụng Backend có sẵn

Nếu bạn đã có backend public:
1. Thêm Secret `VITE_API_URL` với URL backend
2. PR Preview sẽ tự động kết nối

### Cách 3: Chỉ test Frontend UI (Không có backend)

Frontend sẽ hiển thị nhưng không thể upload/chat vì không có backend.
Có thể dùng để review UI/UX.

## 📝 Cấu hình hiện tại

Workflow PR Preview đã được cấu hình để:
- ✅ Sử dụng `VITE_API_URL` secret nếu có
- ✅ Fallback về `localhost:5000` nếu không có secret
- ✅ Build với đúng base path cho GitHub Pages

## 🚀 Test sau khi deploy backend

1. **Thêm Secret**:
   ```
   Name: VITE_API_URL
   Value: https://your-backend-url.com
   ```

2. **Tạo PR mới** hoặc **update PR hiện tại**

3. **Check PR Preview**:
   - Workflow sẽ build lại với API URL mới
   - Frontend sẽ kết nối được với backend

## ⚠️ Lưu ý CORS

Backend cần enable CORS cho domain GitHub Pages:
```python
# backend/app.py
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=[
    "https://nmhung311.github.io",
    "http://localhost:8080",
    "http://localhost:5173"
])
```

Hoặc allow tất cả origins (development only):
```python
CORS(app, resources={r"/*": {"origins": "*"}})
```

