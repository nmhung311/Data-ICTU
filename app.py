#!/usr/bin/env python3
"""
Entry point wrapper for Flask app - for deployment platforms that expect app.py in root
This file simply imports and runs the actual Flask app from backend/app.py
"""

import sys
import os

# Add backend directory to Python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, backend_path)

# Change to backend directory to ensure relative paths work correctly
original_dir = os.getcwd()
os.chdir(backend_path)

try:
    # Import and run the actual Flask app
    from app import app
    
    # Export app for platforms that use 'from app import app'
    # This ensures Flask can find the app instance
    
except Exception as e:
    print(f"Error importing Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

