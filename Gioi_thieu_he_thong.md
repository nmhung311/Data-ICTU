# Giới thiệu hệ thống chuyển đổi và sinh dữ liệu Markdown từ văn bản nguồn

## Mục tiêu

Hệ thống của bạn được xây dựng nhằm:
- Chuyển đổi các loại văn bản nguồn (như PDF, DOCX, TXT, v.v.) thành file Markdown chuẩn.
- Sinh metadata tự động (như doc_id, department, type_data, category, date, source...) từ nội dung tài liệu.
- Tự động phát hiện, phân loại, tách các khối nội dung như “Căn cứ”, “Quyết định”, “Nội dung”, v.v.
- Tích hợp AI (LLM OpenAI GPT-4o-mini hoặc Google Gemini) để sinh keyword, sinh tiêu đề nội dung thông minh cho từng khối.
- Tạo output chuẩn hoá, sẵn sàng nhập kho dữ liệu, dùng cho học máy hoặc phục vụ tra cứu nội bộ.

## Thành phần chính

- **Backend** (Flask REST API & Docker):
  - Nhận file upload, lưu trữ, trích xuất, tách khối nội dung tự động.
  - Tích hợp sinh keyword bằng LLM, sinh tiêu đề động.
  - Quản lý truy xuất và ghi log.
- **Frontend** (HTML/JS đơn giản):
  - Nộp file, xem kết quả markdown sau chuyển đổi, tải xuống.
- **DevOps** (Docker, Docker Compose):
  - Chạy môi trường backend độc lập, hỗ trợ mount code và hot reload khi phát triển.

## Luồng vận hành

1. Người dùng upload file tài liệu gốc.
2. Hệ thống tự tách các phần metadata, nội dung, căn cứ, quyết định…
3. AI sẽ sinh keyword và tiêu đề tự động theo từng khối logic.
4. Xuất kết quả thành 1 hoặc nhiều file Markdown với chuẩn metadata, title nội dung động, không trùng lặp thông tin.
5. Cho phép tải về file kết quả hoặc trích xuất batch nhiều file.

## Điểm nổi bật

- **Tự động hóa tối đa:** Người dùng chỉ cần upload, mọi khối được phân tích và chuẩn hóa tự động.
- **Chuẩn output mở rộng:** Thích hợp cho các kho dữ liệu số hóa, nghiên cứu, đào tạo...
- **Tùy chỉnh linh hoạt:** Dễ mở rộng để nhận nhiều thể loại tài liệu, form metadata.

## Công nghệ sử dụng

- Python 3.11, Flask REST API
- Docker, Docker Compose
- OpenAI GPT-4o-mini, Google Gemini LLM
- PaddleOCR, Tesseract OCR (nhận dạng ký tự tiếng Việt)
- SQLite, Pandas, OpenCV, v.v.

## Thông tin liên hệ
- **Tác giả:** [Điền tên bạn]
- **Github:** [Điền link Github nếu muốn]
- **Email:** [Điền email nếu muốn]

