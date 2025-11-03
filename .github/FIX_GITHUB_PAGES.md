# 🔧 Hướng dẫn Fix GitHub Pages Deploy từ env-dev

## ⚠️ Vấn đề

GitHub Pages đang được cấu hình deploy từ branch `env-dev` (source code branch).
Nhưng cần deploy từ branch `gh-pages` (branch chứa frontend đã build).

## ✅ Giải pháp

### Bước 1: Tạo branch `gh-pages` bằng cách chạy workflow

1. **Vào Actions:**
   https://github.com/nmhung311/Process-Data-chatbot-ICTU/actions

2. **Chọn workflow "Manual Deploy to GitHub Pages":**
   - Click vào workflow name
   - Click nút **"Run workflow"** (bên phải)
   - Chọn branch: `env-dev`
   - Click **"Run workflow"**

3. **Đợi workflow chạy xong (2-3 phút):**
   - Workflow sẽ build frontend
   - Tự động tạo branch `gh-pages` với files đã build
   - Deploy lên branch `gh-pages`

### Bước 2: Kiểm tra branch `gh-pages` đã được tạo

1. Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/branches
2. Tìm branch `gh-pages`
3. Nếu có → ✅ Bước 1 thành công
4. Nếu không có → Đợi thêm hoặc check workflow logs

### Bước 3: Đổi GitHub Pages sang branch `gh-pages`

1. **Vào Settings → Pages:**
   https://github.com/nmhung311/Process-Data-chatbot-ICTU/settings/pages

2. **Thay đổi cấu hình:**
   - **Branch dropdown**: Chọn `gh-pages` (thay vì `env-dev`)
   - **Folder dropdown**: Giữ nguyên `/ (root)`
   - Click **"Save"**

3. **Đợi vài phút:**
   - GitHub sẽ rebuild site từ branch `gh-pages`
   - Frontend sẽ hiển thị tại: `https://nmhung311.github.io/Process-Data-chatbot-ICTU/`

## 📋 Sau khi fix

✅ GitHub Pages sẽ:
- Deploy từ branch `gh-pages` (built frontend)
- Tự động update khi bạn chạy workflow deploy
- Hiển thị frontend đúng cách

## 🔄 Workflow hoạt động

Sau khi fix:
1. Bạn push code vào `env-dev` hoặc `main`
2. Chạy workflow "Manual Deploy" hoặc "Deploy to GitHub Pages"
3. Workflow build frontend → deploy lên `gh-pages`
4. GitHub Pages tự động rebuild từ `gh-pages`
5. Frontend được update!

## ⚠️ Lưu ý

- **KHÔNG** commit trực tiếp vào branch `gh-pages`
- **KHÔNG** thay đổi files trong `gh-pages` thủ công
- Branch `gh-pages` chỉ được update bởi workflow tự động

