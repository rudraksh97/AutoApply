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
            error_message TEXT,
            source_feed TEXT,
            source_feed_name TEXT,
            company_name TEXT,
            job_title TEXT,
            apply_link TEXT
        )
    """)
    
    # Migration: Add new columns if they don't exist
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN source_feed TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN source_feed_name TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN company_name TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN job_title TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN apply_link TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Create drafts table for draft-first workflow
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY,
            job_url TEXT UNIQUE,
            status TEXT NOT NULL,
            form_state_json TEXT,
            resume_path TEXT,
            job_details TEXT,
            apply_link TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Migration: Add apply_link to drafts if it doesn't exist
    try:
        cursor.execute("ALTER TABLE drafts ADD COLUMN apply_link TEXT")
    except sqlite3.OperationalError:
        pass
    
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
