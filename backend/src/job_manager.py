"""
Job management and persistence for the AutoApply application.

This module handles the storage and retrieval of job application statuses
and metadata using a SQLite database.
"""

import json
import os
import sqlite3
from datetime import datetime
from src.database import init_db, get_connection
from src.url_utils import normalize_job_url

class JobManager:
    """
    Manages the job application database using SQLite.
    """
    def __init__(self):
        """Initializes the manager, ensures DB exists, and migrates old JSON data if needed."""
        init_db()
        self._migrate_json_if_needed()

    def _migrate_json_if_needed(self):
        """Migrates data from legacy jobs.json if DB is empty and json exists."""
        json_file = "data/jobs.json"
        
        # Check if JSON exists
        if not os.path.exists(json_file):
            return

        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if DB is empty
            cursor.execute("SELECT count(*) FROM jobs")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"[MIGRATION] Found empty DB and existing {json_file}. Migrating data...")
                try:
                    with open(json_file, 'r') as f:
                        jobs = json.load(f)
                        
                    for job in jobs:
                        # Handle potential missing keys from very old versions
                        url = job.get('url')
                        if not url: continue
                        
                        cursor.execute("""
                            INSERT OR IGNORE INTO jobs (url, status, pdf_path, timestamp, details, error_message)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            url,
                            job.get('status', 'Pending'),
                            job.get('pdf_path'),
                            job.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                            str(job.get('details')) if job.get('details') else None,
                            str(job.get('error_message')) if job.get('error_message') else None
                        ))
                    
                    conn.commit()
                    print(f"[MIGRATION] Successfully migrated {len(jobs)} jobs.")
                    
                    # Rename JSON file to backup
                    os.rename(json_file, json_file + ".bak")
                    print(f"[MIGRATION] Renamed {json_file} to {json_file}.bak")
                    
                except Exception as e:
                    print(f"[MIGRATION] Failed to migrate data: {e}")

    def get_all_jobs(self):
        """
        Retrieves the complete list of jobs.

        Returns:
            list: A list of dictionaries representing individual jobs.
        """
        with get_connection() as conn:
            # Return dicts
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def job_exists(self, url):
        """Checks if a job with the given URL already exists in the database."""
        url = normalize_job_url(url)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM jobs WHERE url = ?", (url,))
            return cursor.fetchone() is not None

    def add_job(self, url, status="Pending", source_feed=None, source_feed_name=None, company_name=None, job_title=None):
        """
        Adds a new job to the database if it doesn't already exist.

        Args:
            url (str): Unique URL of the job posting.
            status (str): Initial status of the job.
            source_feed (str, optional): URL of the RSS feed that sourced this job.
            source_feed_name (str, optional): Name of the RSS feed that sourced this job.
            company_name (str, optional): Name of the company.
            job_title (str, optional): Title of the job role.

        Returns:
            bool: True if added, False if it already existed.
        """
        url = normalize_job_url(url)
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO jobs (url, status, timestamp, source_feed, source_feed_name, company_name, job_title)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (url, status, timestamp, source_feed, source_feed_name, company_name, job_title))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def update_job(self, url, status=None, pdf_path=None, details=None, error_message=None, 
                   source_feed=None, source_feed_name=None, company_name=None, job_title=None, apply_link=None):
        """
        Updates an existing job's status and metadata.

        Args:
            url (str): The unique URL of the job to update.
            status (str, optional): New processing status.
            pdf_path (str, optional): Local path to the generated resume PDF.
            details (str, optional): Extracted job description snippet.
            error_message (str, optional): Error details if processing failed.
            source_feed (str, optional): URL of the RSS feed source.
            source_feed_name (str, optional): Name of the RSS feed source.
            company_name (str, optional): Name of the company.
            job_title (str, optional): Title of the job role.
            apply_link (str, optional): URL of the application page (if different from job URL).

        Returns:
            bool: True if the job was found and updated, False otherwise.
        """
        # Normalize URL before lookup/update
        url = normalize_job_url(url)

        # build update query dynamically
        fields = []
        values = []
        
        if status:
            fields.append("status = ?")
            values.append(status)
        if pdf_path:
            fields.append("pdf_path = ?")
            values.append(pdf_path)
        if details:
            fields.append("details = ?")
            values.append(str(details))
        if source_feed:
            fields.append("source_feed = ?")
            values.append(source_feed)
        if source_feed_name:
            fields.append("source_feed_name = ?")
            values.append(source_feed_name)
        if company_name:
            fields.append("company_name = ?")
            values.append(company_name)
        if job_title:
            fields.append("job_title = ?")
            values.append(job_title)
        if apply_link:
            fields.append("apply_link = ?")
            values.append(apply_link)
        
        # Always update error message if provided (even if None/empty to clear it)
        if error_message is not None:
             fields.append("error_message = ?")
             values.append(str(error_message) if error_message else None)

        # Always update timestamp on change
        fields.append("timestamp = ?")
        values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if not fields:
            return True # Nothing to update

        values.append(url) # For WHERE clause
        
        query = f"UPDATE jobs SET {', '.join(fields)} WHERE url = ?"
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_job(self, url):
        """
        Deletes a job and its associated draft from the database.

        Args:
            url (str): The unique URL of the job to delete.

        Returns:
            bool: True if the job was found and deleted, False otherwise.
        """
        url = normalize_job_url(url)

        from src.draft_manager import DraftManager
        DraftManager().delete_draft_by_url(url)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE url = ?", (url,))
            conn.commit()
            return cursor.rowcount > 0

    def mark_as_sent(self, url, sent=True):
        """
        Marks a job as sent (application submitted).

        Args:
            url (str): The unique URL of the job.
            sent (bool): True to mark as sent, False to unmark.

        Returns:
            bool: True if the job was found and updated, False otherwise.
        """
        url = normalize_job_url(url)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET sent = ? WHERE url = ?", (1 if sent else 0, url))
            conn.commit()
            return cursor.rowcount > 0

    def increment_retry_count(self, url):
        """
        Increments the retry count for a job.
        
        Args:
            url (str): The unique URL of the job.
            
        Returns:
            bool: True if updated, False otherwise.
        """
        url = normalize_job_url(url)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET retry_count = retry_count + 1 WHERE url = ?", (url,))
            conn.commit()
            return cursor.rowcount > 0
