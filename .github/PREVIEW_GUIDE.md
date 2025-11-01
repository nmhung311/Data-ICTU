# 🖼️ Hướng dẫn thêm Preview Link trên GitHub

## Cách 1: Thêm Website vào phần "About" ⭐ (Khuyến nghị)

### Bước 1: Tìm phần "About"
1. Vào repository: https://github.com/nmhung311/Process-Data-chatbot-ICTU
2. Ở **bên phải** trang chủ repo, scroll lên trên cùng
3. Bạn sẽ thấy phần **"About"** với thông tin repo

### Bước 2: Edit About
1. Click vào **icon ⚙️** (gear icon) hoặc **icon bút chì** bên cạnh "About"
   - Nếu không thấy icon, có thể About đang ở chế độ collapsed, click vào text "About" để expand

### Bước 3: Điền thông tin
Trong popup/modal hiện ra, điền:
- **☐ Website** (checkbox): Tick vào và thêm URL
  - Ví dụ: `https://your-demo-site.com` hoặc `https://nmhung311.github.io/Process-Data-chatbot-ICTU`
- **Description**: `Upload PDF, extract text, and chat with documents using AI`
- **Topics** (tags): 
  - `react`
  - `flask` 
  - `docker`
  - `pdf-processing`
  - `chatbot`
  - `openai`

### Bước 4: Lưu
Click **Save changes**

### ⚠️ Lưu ý:
- Nếu không thấy phần "About", có thể đang ẩn. Hãy scroll lên trên cùng bên phải trang.
- Nếu không thấy nút edit, bạn cần có quyền admin/owner của repo.

## Cách 2: Thêm Social Preview Image

Preview image sẽ hiển thị khi share link repo trên social media hoặc chat.

### Tùy chọn A: Sử dụng file trong repo

1. Tạo screenshot của ứng dụng (kích thước 1200x630px)
2. Đặt tên: `preview.png` hoặc `og-image.png`
3. Upload vào folder `docs/` hoặc root của repo
4. GitHub sẽ tự động detect và sử dụng

### Tùy chọn B: Sử dụng meta tags trong README

Đã được thêm vào README.md với placeholder image. 
Thay thế URL placeholder bằng screenshot thực tế.

## Cách 3: Enable GitHub Pages

1. Vào **Settings** → **Pages** (menu bên trái)
2. **Source**: Chọn branch (ví dụ: `main`, `env-dev`, hoặc `gh-pages`)
3. **Folder**: Chọn `/ (root)` hoặc `/docs`
4. Click **Save**
5. Sau vài phút, GitHub Pages sẽ có tại:
   `https://nmhung311.github.io/Process-Data-chatbot-ICTU`

## Cách 4: Thêm vào README.md (Đã làm)

Đã thêm badges, links, và preview section vào README.md.
Preview sẽ hiển thị khi:
- Xem README trên GitHub
- Share link repo
- Clone/download repo

## Kết quả

Sau khi làm xong, preview sẽ hiển thị:
- ✅ Website link trong phần About
- ✅ Social preview khi share link
- ✅ GitHub Pages URL (nếu enable)
- ✅ Badges và links trong README

