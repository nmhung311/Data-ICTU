# 🔧 Troubleshooting Workflow bị treo

## Vấn đề: Workflow bị treo khi deploy

### ✅ Đã sửa:
- Thêm timeout cho job (10 phút)
- Thêm timeout cho từng step (5 phút)
- Thêm git config cho deploy action

## 🔍 Nếu vẫn bị treo:

### 1. Kiểm tra Workflow Logs

1. Vào: https://github.com/nmhung311/Process-Data-chatbot-ICTU/actions
2. Click vào workflow run đang bị treo
3. Xem step nào đang stuck:
   - Yellow circle = đang chạy
   - Red X = failed
   - Green check = thành công

### 2. Các nguyên nhân thường gặp:

#### a) npm install/build quá lâu
**Triệu chứng**: Stuck ở step "Install dependencies" hoặc "Build frontend"
**Giải pháp**:
- Check package.json có dependency nào lớn không
- Có thể dùng npm cache để tăng tốc

#### b) Deploy action bị stuck
**Triệu chứng**: Stuck ở step "Deploy to GitHub Pages"
**Giải pháp**:
- Check permissions (Settings > Actions > Workflow permissions = Read and write)
- Check branch `env-dev` có tồn tại không
- Có thể do network issues, cancel và chạy lại

#### c) Permissions issues
**Triệu chứng**: Workflow failed với lỗi permission
**Giải pháp**:
1. Settings → Actions → General
2. Workflow permissions → Read and write permissions
3. Save

### 3. Cách xử lý:

#### Cancel và chạy lại:
1. Click vào workflow run đang bị treo
2. Click "Cancel workflow" (nếu có)
3. Chạy lại workflow

#### Check branch permissions:
```bash
# Kiểm tra branch có tồn tại
git ls-remote --heads origin env-dev
```

#### Tăng timeout (nếu cần):
Sửa trong workflow:
```yaml
timeout-minutes: 15  # Tăng từ 10 lên 15
```

### 4. Debug steps:

1. **Xem logs chi tiết**:
   - Click vào step đang stuck
   - Scroll xuống xem output
   - Tìm error messages

2. **Check npm install**:
   - Nếu stuck ở "npm ci", có thể do:
     - package-lock.json conflict
     - Network timeout
     - Dependencies quá lớn

3. **Check build**:
   - Nếu stuck ở "npm run build", có thể do:
     - Build process quá lâu
     - Memory issues
     - TypeScript errors (check logs)

4. **Check deploy**:
   - Nếu stuck ở "Deploy to GitHub Pages", có thể do:
     - Permissions issues
     - Branch không tồn tại
     - Git push failed

## 🔄 Giải pháp nhanh:

### Option 1: Cancel và chạy lại
1. Cancel workflow hiện tại
2. Chạy lại workflow mới

### Option 2: Check và fix
1. Xem logs để tìm nguyên nhân
2. Fix vấn đề (permissions, branch, etc.)
3. Chạy lại workflow

### Option 3: Deploy thủ công (tạm thời)
```bash
cd frontend
npm install
npm run build
# Upload folder dist/ lên GitHub thủ công
```

## 📝 Best practices:

- ✅ Luôn check workflow logs
- ✅ Đảm bảo permissions đúng
- ✅ Sử dụng timeout để tránh treo lâu
- ✅ ✅ Monitor workflow runs thường xuyên

