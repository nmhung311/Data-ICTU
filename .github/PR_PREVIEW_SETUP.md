# 🚀 Hướng dẫn Setup PR Preview trên GitHub

## 📋 Yêu cầu trước khi setup

1. **Enable GitHub Pages:**
   - Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/settings/pages
   - **Source**: Chọn `Deploy from a branch`
   - **Branch**: Chọn `gh-pages` → `/ (root)`
   - Click **Save**

2. **Grant Actions permission:**
   - Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/settings/actions
   - Scroll xuống **Workflow permissions**
   - Chọn **Read and write permissions**
   - Click **Save**

## 🎯 Cách hoạt động

### PR Preview Workflow (`.github/workflows/pr-preview.yml`)

Workflow này sẽ tự động:
- ✅ Build frontend khi PR được mở/cập nhật
- ✅ Deploy preview lên GitHub Pages tại: `https://nmhung311.github.io/Process-Data-chatbot-ICTU/pr-preview/pr-[number]/`
- ✅ Tạo comment trên PR với link preview
- ✅ Tự động xóa preview khi PR được đóng

### Main Deployment Workflow (`.github/workflows/deploy-pages.yml`)

Workflow này sẽ:
- ✅ Deploy main site lên GitHub Pages khi push vào `main` branch
- ✅ Giữ nguyên các PR previews (không xóa)

## 📝 Cấu hình bổ sung (Tùy chọn)

### 1. Thêm Environment Variable cho API URL

Nếu bạn muốn frontend kết nối với backend khác trong preview:

1. Vào: Repository → Settings → Secrets and variables → Actions
2. Thêm Secret mới: `VITE_API_URL`
3. Giá trị: `https://your-backend-api.com`

Workflow sẽ tự động dùng secret này khi build.

### 2. Custom Preview URL

Preview URLs sẽ có format:
```
https://nmhung311.github.io/Process-Data-chatbot-ICTU/pr-preview/pr-[PR_NUMBER]/
```

Ví dụ PR #5:
```
https://nmhung311.github.io/Process-Data-chatbot-ICTU/pr-preview/pr-5/
```

## 🔍 Kiểm tra

1. **Tạo Pull Request:**
   ```bash
   git checkout -b feature/test-preview
   git push origin feature/test-preview
   ```
   Sau đó tạo PR trên GitHub.

2. **Xem Preview:**
   - Workflow sẽ chạy tự động
   - Sau khi deploy xong, sẽ có comment trên PR với link preview
   - Click vào link để xem preview

3. **Check GitHub Pages:**
   - Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/deployments
   - Xem deployment status

## ⚠️ Lưu ý

- **Backend API:** PR Preview chỉ deploy frontend. Backend vẫn chạy ở localhost hoặc server riêng.
- **API URL:** Nếu backend không public, frontend trong preview có thể không kết nối được với API.
- **Build time:** Mỗi lần push commit mới vào PR, preview sẽ được update tự động.

## 🐛 Troubleshooting

### Preview không hiển thị
1. Check workflow đã chạy: Actions → PR Preview workflow
2. Check GitHub Pages đã enable chưa
3. Check branch `gh-pages` đã được tạo chưa

### Preview bị lỗi 404
- Đảm bảo `base` path trong `vite.config.ts` đúng với repo name
- Check deployment branch là `gh-pages`

### Frontend không kết nối được API
- Backend cần public hoặc sử dụng proxy
- Update `VITE_API_URL` secret nếu cần

## 📚 Tài liệu tham khảo

- [PR Preview Action](https://github.com/rossjrw/pr-preview-action)
- [GitHub Pages Deploy Action](https://github.com/JamesIves/github-pages-deploy-action)

