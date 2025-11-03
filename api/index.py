"""
Vercel Serverless Function Handler cho Flask App
Vercel Python runtime tự động detect WSGI application
"""

import sys
import os

# Thêm backend vào Python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Đổi working directory về backend để relative paths hoạt động đúng
os.chdir(backend_path)

# Import Flask app từ backend
from app import app

# Vercel Python runtime tự động detect app như WSGI application
# Chỉ cần export app, Vercel sẽ tự động handle

