#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database module for Raw2MD Agent Backend
SQLite database operations and management
"""

import sqlite3
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """SQLite database manager for Raw2MD Agent"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time REAL,
                    status TEXT DEFAULT 'completed',
                    error_message TEXT,
                    metadata TEXT,
                    stats TEXT,
                    markdown_content TEXT,
                    cleaned_text TEXT,
                    raw_text TEXT,
                    output_path TEXT
                )
            ''')
            
            # Create metadata_blocks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata_blocks (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    department TEXT NOT NULL DEFAULT 'Training Department',
                    type_data TEXT NOT NULL DEFAULT 'markdown',
                    category TEXT NOT NULL,
                    date TEXT,
                    source TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES sources (id)
                )
            ''')
            
            # Create sources table for uploaded files tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_path TEXT NOT NULL
                )
            ''')
            
            # Create files table for uploaded files tracking (legacy)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_path TEXT NOT NULL
                )
            ''')
            
            # Create processing_stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT CURRENT_DATE,
                    files_processed INTEGER DEFAULT 0,
                    total_processing_time REAL DEFAULT 0,
                    avg_processing_time REAL DEFAULT 0,
                    error_count INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_result(self, result_data: Dict[str, Any]) -> str:
        """Save processing result to database"""
        result_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO results (
                    id, filename, file_type, file_size, processing_time,
                    status, error_message, metadata, stats, markdown_content,
                    cleaned_text, raw_text, output_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_id,
                result_data.get('filename'),
                result_data.get('file_type'),
                result_data.get('file_size'),
                result_data.get('processing_time'),
                result_data.get('status', 'completed'),
                result_data.get('error_message'),
                json.dumps(result_data.get('metadata', {})),
                json.dumps(result_data.get('stats', {})),
                result_data.get('markdown_content'),
                result_data.get('cleaned_text'),
                result_data.get('raw_text'),
                str(result_data.get('output_path')) if result_data.get('output_path') else None  # Convert to string
            ))
            
            conn.commit()
            logger.info(f"Result saved with ID: {result_id}")
            return result_id
    
    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Get processing result by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM results WHERE id = ?', (result_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'filename': row['filename'],
                    'file_type': row['file_type'],
                    'file_size': row['file_size'],
                    'upload_time': row['upload_time'],
                    'processing_time': row['processing_time'],
                    'status': row['status'],
                    'error_message': row['error_message'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'stats': json.loads(row['stats']) if row['stats'] else {},
                    'markdown_content': row['markdown_content'],
                    'cleaned_text': row['cleaned_text'],
                    'raw_text': row['raw_text'],
                    'output_path': row['output_path']
                }
            return None
    
    def list_results(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List processing results with pagination"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, filename, file_type, file_size, upload_time, 
                       processing_time, status, error_message
                FROM results 
                ORDER BY upload_time DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def save_source(self, file_data: Dict[str, Any]) -> str:
        """Save uploaded source file information"""
        file_id = str(uuid.uuid4())
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sources (id, filename, file_type, file_size, file_path)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    file_id,
                    file_data.get('filename'),
                    file_data.get('file_type'),
                    file_data.get('file_size'),
                    str(file_data.get('file_path'))  # Convert to string
                ))
                
                conn.commit()
                logger.info(f"Source saved to database: {file_id}")
                return file_id
        except Exception as e:
            logger.error(f"Failed to save source to database: {e}")
            raise
    
    def save_file(self, file_data: Dict[str, Any]) -> str:
        """Save uploaded file information (legacy)"""
        file_id = str(uuid.uuid4())
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO files (id, filename, file_type, file_size, file_path)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    file_id,
                    file_data.get('filename'),
                    file_data.get('file_type'),
                    file_data.get('file_size'),
                    str(file_data.get('file_path'))  # Convert to string
                ))
                
                conn.commit()
                logger.info(f"File saved to database: {file_id}")
                return file_id
        except Exception as e:
            logger.error(f"Failed to save file to database: {e}")
            raise
    
    def list_files(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List uploaded files with pagination"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, filename, file_type, file_size, upload_time
                FROM files 
                ORDER BY upload_time DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total results
            cursor.execute('SELECT COUNT(*) as total FROM results')
            total_results = cursor.fetchone()['total']
            
            # Successful results
            cursor.execute('SELECT COUNT(*) as successful FROM results WHERE status = "completed"')
            successful_results = cursor.fetchone()['successful']
            
            # Error results
            cursor.execute('SELECT COUNT(*) as errors FROM results WHERE status = "error"')
            error_results = cursor.fetchone()['errors']
            
            # Average processing time
            cursor.execute('SELECT AVG(processing_time) as avg_time FROM results WHERE processing_time IS NOT NULL')
            avg_time = cursor.fetchone()['avg_time'] or 0
            
            # Total files uploaded
            cursor.execute('SELECT COUNT(*) as total_files FROM files')
            total_files = cursor.fetchone()['total_files']
            
            return {
                'total_results': total_results,
                'successful_results': successful_results,
                'error_results': error_results,
                'success_rate': (successful_results / total_results * 100) if total_results > 0 else 0,
                'average_processing_time': round(avg_time, 2),
                'total_files_uploaded': total_files
            }
    
    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get source file information by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sources WHERE id = ?', (source_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def list_sources(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List source files with pagination"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, filename, file_type, file_size, upload_time, file_path
                FROM sources 
                ORDER BY upload_time DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def delete_source(self, source_id: str) -> bool:
        """Delete source from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sources WHERE id = ?', (source_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file from database (legacy)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def update_file(self, file_id: str, updates: Dict[str, Any]) -> bool:
        """Update file information"""
        if not updates:
            return False
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in ['filename', 'file_type', 'file_size', 'file_path']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(file_id)
            query = f"UPDATE files SET {', '.join(set_clauses)} WHERE id = ?"
            
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def cleanup_old_results(self, days: int = 30):
        """Clean up old results older than specified days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM results 
                WHERE upload_time < datetime('now', '-{} days')
            '''.format(days))
            
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old results")
            return deleted_count
