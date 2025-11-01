# 🚀 Deploy trực tiếp từ branch env-dev

## ✅ Đã cấu hình để deploy trực tiếp vào branch env-dev

### Cách hoạt động:

1. **Workflow sẽ build frontend** từ source code trong `env-dev`
2. **Deploy folder `frontend/dist`** (đã build) vào chính branch `env-dev`
3. **GitHub Pages deploy từ branch `env-dev`**
4. ✅ **Không cần branch `gh-pages` riêng!**

## 📋 Các bước:

### Bước 1: Chạy Workflow

1. Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/actions
2. Chọn **"Manual Deploy to GitHub Pages"**
3. Click **"Run workflow"**
4. Branch: `env-dev` (mặc định)
5. Click **"Run workflow"**
6. Đợi 2-3 phút

### Bước 2: Setup GitHub Pages

1. Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/settings/pages
2. **Branch**: `env-dev` (chọn branch này)
3. **Folder**: `/frontend/dist` (folder chứa built files)
4. Click **"Save"**

### Hoặc nếu muốn deploy vào root của env-dev:

1. **Branch**: `env-dev`
2. **Folder**: `/` (root)
   - ⚠️ Lưu ý: Cần đảm bảo workflow deploy vào root của branch

## ✅ Kết quả:

Frontend sẽ live tại:
```
https://nmhung311.github.io/Process-Data-chatbot-ICTU/
```

## 🔄 Update:

Mỗi lần muốn update:
1. Push code mới lên `env-dev`
2. Chạy workflow "Manual Deploy"
3. Frontend tự động update

## ⚠️ Lưu ý:

- Workflow sẽ commit folder `dist/` vào branch `env-dev`
- Không cần branch `gh-pages` riêng nữa
- Có thể xóa branch `gh-pages` nếu không dùng

