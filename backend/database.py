import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict

DB_PATH = 'documents.db'

def init_db():
    """Khởi tạo database và tạo bảng nếu chưa tồn tại"""
    conn = sqlite3.connect(DB_PATH)
    # Đảm bảo SQLite sử dụng UTF-8
    conn.execute("PRAGMA encoding = 'UTF-8'")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            ocr_text TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # Thêm cột metadata nếu chưa có (migration)
    try:
        cursor.execute('ALTER TABLE documents ADD COLUMN metadata TEXT')
        conn.commit()
        print("✅ Đã thêm cột metadata vào bảng documents")
    except sqlite3.OperationalError:
        # Cột đã tồn tại, không cần làm gì
        pass
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_PATH}")


def save_document(document_id: str, filename: str, filepath: str, ocr_text: str, metadata: str = None) -> bool:
    """Lưu document vào database với xử lý encoding UTF-8"""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Đảm bảo sử dụng UTF-8
        conn.execute("PRAGMA encoding = 'UTF-8'")
        cursor = conn.cursor()
        
        # Đảm bảo ocr_text là string và được encode đúng cách
        if ocr_text and not isinstance(ocr_text, str):
            ocr_text = str(ocr_text)
        if metadata and not isinstance(metadata, str):
            metadata = str(metadata)
        # SQLite sẽ tự động xử lý UTF-8 nếu text đã là unicode string
        
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO documents 
            (document_id, filename, filepath, ocr_text, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (document_id, filename, filepath, ocr_text, metadata, now, now))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Lỗi khi lưu document: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_document_metadata(document_id: str, metadata: str) -> bool:
    """Cập nhật metadata cho document"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA encoding = 'UTF-8'")
        cursor = conn.cursor()
        
        if metadata and not isinstance(metadata, str):
            metadata = str(metadata)
        
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE documents 
            SET metadata = ?, updated_at = ?
            WHERE document_id = ?
        ''', (metadata, now, document_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật metadata: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_document(document_id: str) -> Optional[Dict]:
    """Lấy document từ database theo document_id"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM documents WHERE document_id = ?
        ''', (document_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # sqlite3.Row không có method .get(), phải dùng try/except hoặc kiểm tra key
            result = {
                'id': row['id'],
                'document_id': row['document_id'],
                'filename': row['filename'],
                'filepath': row['filepath'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            # Kiểm tra các cột có thể không tồn tại
            try:
                result['ocr_text'] = row['ocr_text']
            except (KeyError, IndexError):
                result['ocr_text'] = None
            try:
                result['metadata'] = row['metadata']
            except (KeyError, IndexError):
                result['metadata'] = None
            return result
        return None
    except Exception as e:
        print(f"❌ Lỗi khi lấy document: {e}")
        return None


def get_all_documents() -> list:
    """Lấy tất cả documents"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM documents ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách documents: {e}")
        return []


def delete_document(document_id: str) -> tuple:
    """Xóa document từ database theo document_id"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Lấy filepath trước khi xóa để xóa file vật lý
        cursor.execute('SELECT filepath FROM documents WHERE document_id = ?', (document_id,))
        row = cursor.fetchone()
        
        if row:
            filepath = row[0]
            
            # Xóa khỏi database
            cursor.execute('DELETE FROM documents WHERE document_id = ?', (document_id,))
            conn.commit()
            conn.close()
            
            # Xóa file vật lý nếu tồn tại
            # Xử lý cả relative path và absolute path
            if filepath:
                # Nếu là relative path, cần lấy đường dẫn tuyệt đối từ thư mục backend
                if not os.path.isabs(filepath):
                    # Lấy thư mục chứa database.py (backend folder)
                    backend_dir = os.path.dirname(os.path.abspath(__file__))
                    absolute_filepath = os.path.join(backend_dir, filepath)
                else:
                    absolute_filepath = filepath
                
                # Kiểm tra và xóa file
                if os.path.exists(absolute_filepath):
                    try:
                        os.remove(absolute_filepath)
                        print(f"✅ Đã xóa file vật lý: {absolute_filepath}")
                    except Exception as e:
                        print(f"⚠️ Không thể xóa file vật lý {absolute_filepath}: {e}")
                        # Vẫn trả về True vì đã xóa khỏi DB, chỉ cảnh báo về file
                else:
                    print(f"⚠️ File không tồn tại (có thể đã bị xóa trước đó): {absolute_filepath}")
            
            return True, "Đã xóa document thành công"
        else:
            conn.close()
            return False, "Document không tồn tại"
    except Exception as e:
        print(f"❌ Lỗi khi xóa document: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Lỗi khi xóa document: {str(e)}"

