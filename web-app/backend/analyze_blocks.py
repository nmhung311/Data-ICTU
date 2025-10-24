#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script hiển thị thông tin các blocks đã tạo

Author: AI Assistant
Date: 2024
"""

import re
import os
from typing import List, Dict, Any

def analyze_blocks_file(file_path: str):
    """Phân tích file blocks đã tạo"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tìm các blocks
    blocks = content.split('---')
    
    print(f"File: {file_path}")
    print(f"Tong so blocks: {len(blocks)}")
    print("=" * 60)
    
    for i, block in enumerate(blocks):
        if not block.strip():
            continue
            
        # Tìm metadata
        metadata_match = re.search(r'## Metadata\s*\n- \*\*doc_id\*\*:\s*(.+?)\n- \*\*data_type\*\*:\s*(.+?)\n- \*\*category\*\*:\s*(.+?)\n- \*\*date\*\*:\s*(.+?)\n- \*\*source\*\*:\s*(.+?)\n', block, re.DOTALL)
        
        if metadata_match:
            doc_id = metadata_match.group(1).strip()
            data_type = metadata_match.group(2).strip()
            category = metadata_match.group(3).strip()
            date = metadata_match.group(4).strip()
            source = metadata_match.group(5).strip()
            
            # Tìm title
            title_match = re.search(r'## Tieu de\s*\n\s*(.+?)\n\s*## Noi dung', block, re.DOTALL)
            title = title_match.group(1).strip() if title_match else "Khong co tieu de"
            
            # Tìm content
            content_match = re.search(r'## Noi dung\s*\n\s*(.+?)$', block, re.DOTALL)
            content_text = content_match.group(1).strip() if content_match else ""
            
            print(f"Block {i+1}:")
            print(f"  Source: {source}")
            print(f"  Title: {title}")
            print(f"  Category: {category}")
            print(f"  Content length: {len(content_text)} characters")
            print(f"  Preview: {content_text[:100]}...")
            print()

def main():
    """Chạy phân tích"""
    file_path = "data/uploads/test_8_blocks.md"
    
    if os.path.exists(file_path):
        analyze_blocks_file(file_path)
    else:
        print(f"File {file_path} khong ton tai!")

if __name__ == "__main__":
    main()
