# API Documentation

## Endpoints

### POST /api/process
Xử lý văn bản pháp lý

**Request:**
```json
{
  "text": "Nội dung văn bản",
  "api_key": "gemini_api_key"
}
```

**Response:**
```json
{
  "status": "success",
  "blocks": [
    {
      "metadata": {
        "doc_id": "429/QĐ-ĐHCNT&TT",
        "category": "training_and_regulations",
        "source": "Điều 1",
        "date": "2022-06-22",
        "modify": "",
        "partial_mod": false,
        "data_type": "markdown",
        "amend": ""
      },
      "content": "Nội dung điều khoản..."
    }
  ]
}
```

### GET /api/health
Kiểm tra trạng thái hệ thống

### GET /api/supported-formats
Lấy danh sách định dạng file hỗ trợ
