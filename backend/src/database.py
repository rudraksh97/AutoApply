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
            initial_ats_score INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Create resume_versions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_versions (
            id TEXT PRIMARY KEY,
            draft_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            tex_path TEXT,
            pdf_path TEXT,
            ats_score INTEGER,
            justification TEXT,
            keywords_added TEXT,
            changes_summary TEXT,
            status TEXT DEFAULT 'COMPLETED',
            is_current INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (draft_id) REFERENCES drafts (id)
        )
    """)
    
    # Migration: Add new columns if they don't exist
    try:
        cursor.execute("ALTER TABLE resume_versions ADD COLUMN status TEXT DEFAULT 'COMPLETED'")
    except sqlite3.OperationalError:
        pass
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
    
    # Migration: Add apply_link to drafts if it doesn't exist
    try:
        cursor.execute("ALTER TABLE drafts ADD COLUMN apply_link TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE drafts ADD COLUMN initial_ats_score INTEGER")
    except sqlite3.OperationalError:
        pass

    # Migration: Add sent column to jobs
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN sent INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Migration: Add retry_count column to jobs
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN retry_count INTEGER DEFAULT 0")
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
