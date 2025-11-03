#!/usr/bin/env python3
"""
Entry point cho deployment platforms
Platform sẽ tìm Flask app ở root directory trước khi đọc Procfile
File này chỉ import và export app từ backend/app.py
"""

import sys
import os

# Thay đổi working directory về backend để các relative path hoạt động đúng
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
original_cwd = os.getcwd()

# Thêm backend vào Python path TRƯỚC KHI import
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Đổi working directory về backend để database, uploads folder hoạt động đúng
os.chdir(backend_path)

# Import Flask app từ backend - dùng importlib để tránh conflict
import importlib.util
spec = importlib.util.spec_from_file_location("backend_app", os.path.join(backend_path, "app.py"))
backend_app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_app_module)

# Export app từ backend module
app = backend_app_module.app

# Export app để platform có thể detect
# Platform sẽ chạy: from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

