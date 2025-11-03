# 🚀 Hướng dẫn Deploy Frontend lên GitHub Pages (Đơn giản)

## Mục tiêu: Live frontend tại `https://nmhung311.github.io/Process-Data-chatbot-ICTU/`

## 📋 Các bước đơn giản:

### Bước 1: Chạy Workflow để Deploy

1. **Vào Actions:**
   https://github.com/nmhung311/Process-Data-chatbot-ICTU/actions

2. **Chọn workflow "Manual Deploy to GitHub Pages":**
   - Click vào workflow name ở sidebar bên trái
   - Hoặc tìm trong danh sách workflows

3. **Click "Run workflow":**
   - Ở bên phải có nút "Run workflow" (dropdown)
   - Click vào dropdown → chọn "Run workflow"
   - **Branch**: Để mặc định `env-dev` hoặc chọn branch bạn muốn
   - Click **"Run workflow"** (nút xanh)

4. **Đợi workflow chạy (2-3 phút):**
   - Xem progress ở tab "Actions"
   - Đợi đến khi thấy dấu ✅ (green checkmark)
   - Workflow sẽ tự động:
     - Build frontend
     - Tạo branch `gh-pages`
     - Deploy lên `gh-pages`

### Bước 2: Setup GitHub Pages

1. **Vào Settings → Pages:**
   https://github.com/nmhung311/Process-Data-chatbot-ICTU/settings/pages

2. **Cấu hình:**
   - **Source**: Deploy from a branch
   - **Branch**: Chọn `gh-pages` (sau khi workflow chạy xong, branch này sẽ xuất hiện)
   - **Folder**: `/ (root)`
   - Click **"Save"**

3. **Đợi 1-2 phút:**
   - GitHub sẽ build và deploy site
   - Bạn sẽ thấy thông báo: "Your site is live at..."

### Bước 3: Truy cập Frontend Live

Sau khi hoàn thành, frontend sẽ live tại:
```
https://nmhung311.github.io/Process-Data-chatbot-ICTU/
```

## ✅ Kết quả

- ✅ Frontend live trên GitHub Pages
- ✅ Có thể share URL với người khác
- ✅ Tự động update khi chạy workflow deploy

## 🔄 Update Frontend

Mỗi khi muốn update frontend:
1. Push code mới lên branch `env-dev`
2. Chạy lại workflow "Manual Deploy to GitHub Pages"
3. Frontend sẽ tự động update sau 2-3 phút

## ⚠️ Lưu ý

- Backend vẫn cần chạy local hoặc deploy riêng
- Frontend sẽ hiển thị nhưng không kết nối được backend nếu backend không public
- Để frontend hoạt động đầy đủ, cần deploy backend public và thêm secret `VITE_API_URL`

