"""
Database connection and initialization module for AutoApply.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_FILE = "data/jobs.db"

def init_db():
    """Initializes the database with the required schema."""
    if not os.path.exists("data"):
        os.makedirs("data")
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            url TEXT PRIMARY KEY,
            status TEXT,
            pdf_path TEXT,
            timestamp TEXT,
            details TEXT,
            error_message TEXT
        )
    """)
    
    # Create drafts table for draft-first workflow
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY,
            job_url TEXT UNIQUE,
            status TEXT NOT NULL,
            form_state_json TEXT,
            resume_path TEXT,
            job_details TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def get_db_path():
    return DB_FILE

@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()
