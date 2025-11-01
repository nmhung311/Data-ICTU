# ✅ Checklist Kiểm tra Deploy Frontend

## 🔍 Vấn đề: "Deploy ra backend"

### Nguyên nhân có thể:

1. **Đang xem nhầm URL**
   - ✅ Frontend URL: `https://nmhung311.github.io/Process-Data-chatbot-ICTU/`
   - ❌ Backend URL: `http://localhost:5000` (chỉ local)

2. **GitHub Pages trỏ sai branch/folder**
   - Settings → Pages → Branch: phải là `gh-pages`
   - Settings → Pages → Folder: phải là `/ (root)`

3. **Workflow chưa chạy hoặc lỗi**
   - Vào Actions tab xem workflow có chạy không
   - Check logs xem có lỗi build không

## ✅ Kiểm tra từng bước:

### Bước 1: Check GitHub Pages Settings

1. Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/settings/pages
2. Kiểm tra:
   - **Source**: `Deploy from a branch`
   - **Branch**: `gh-pages`
   - **Folder**: `/ (root)`
3. Nếu sai → Sửa và Save

### Bước 2: Check Workflow đã chạy chưa

1. Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/actions
2. Tìm workflow: **"Manual Deploy to GitHub Pages"** hoặc **"Deploy to GitHub Pages"**
3. Check:
   - ✅ Status: Green (thành công)
   - ❌ Status: Red (có lỗi) → Click vào xem logs

### Bước 3: Check Deployment

1. Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/deployments
2. Xem deployment mới nhất:
   - ✅ Status: Active
   - ❌ Status: Failed → Click xem chi tiết

### Bước 4: Check Branch gh-pages

1. Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/tree/gh-pages
2. Kiểm tra có file `index.html` không:
   - ✅ Có → Frontend đã được deploy
   - ❌ Không → Chưa deploy hoặc deploy sai

### Bước 5: Truy cập đúng URL

**Frontend (GitHub Pages):**
```
https://nmhung311.github.io/Process-Data-chatbot-ICTU/
```

**Backend (Local - chỉ chạy khi local):**
```
http://localhost:5000
```

⚠️ **Lưu ý**: Backend KHÔNG được deploy lên GitHub Pages. Chỉ có frontend được deploy.

## 🔧 Nếu vẫn thấy "backend":

### Cách 1: Chạy Manual Deploy lại

1. Vào Actions
2. Chọn "Manual Deploy to GitHub Pages"
3. Click "Run workflow"
4. Chọn branch: `env-dev`
5. Click "Run workflow"
6. Đợi 2-3 phút

### Cách 2: Check Workflow Logs

1. Vào Actions → Workflow run mới nhất
2. Click vào job "deploy"
3. Xem logs:
   - ✅ "Deploy to GitHub Pages" step thành công
   - ❌ Có lỗi → Copy error và fix

### Cách 3: Kiểm tra Frontend Build

1. Clone repo và build local:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
2. Check folder `frontend/dist`:
   - ✅ Có file `index.html`
   - ✅ Có các file JS/CSS

## 📝 Checklist nhanh:

- [ ] GitHub Pages enabled (Settings > Pages)
- [ ] Branch: `gh-pages`
- [ ] Folder: `/ (root)`
- [ ] Workflow đã chạy thành công (Actions tab)
- [ ] Deployment active (Deployments tab)
- [ ] Branch `gh-pages` có file `index.html`
- [ ] Truy cập đúng URL: `https://nmhung311.github.io/Process-Data-chatbot-ICTU/`

