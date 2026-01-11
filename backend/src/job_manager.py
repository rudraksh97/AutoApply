"""
Job management and persistence for the AutoApply application.

This module handles the storage and retrieval of job application statuses
and metadata using a local JSON file as a lightweight database.
"""

import json
import os
from datetime import datetime

JOBS_FILE = "data/jobs.json"

class JobManager:
    """
    Manages the job application database.

    Handles adding new jobs, updating their status, and retrieving the 
    history of all processed or pending jobs.
    """
    def __init__(self):
        """Initializes the manager and ensures the data directory and file exist."""
        self._ensure_file()

    def _ensure_file(self):
        """Creates the data directory and jobs JSON file if they do not exist."""
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(JOBS_FILE):
            with open(JOBS_FILE, 'w') as f:
                json.dump([], f)

    def _load(self):
        """Loads all jobs from the JSON file."""
        try:
            with open(JOBS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, data):
        """Saves the provided job data list to the JSON file."""
        with open(JOBS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def get_all_jobs(self):
        """
        Retrieves the complete list of jobs.

        Returns:
            list: A list of dictionaries representing individual jobs.
        """
        return self._load()

    def job_exists(self, url):
        """Checks if a job with the given URL already exists in the database."""
        jobs = self._load()
        return any(job['url'] == url for job in jobs)

    def add_job(self, url, status="Pending"):
        """
        Adds a new job to the database if it doesn't already exist.

        Args:
            url (str): Unique URL of the job posting.
            status (str): Initial status of the job.

        Returns:
            bool: True if added, False if it already existed.
        """
        if self.job_exists(url):
            return False
            
        jobs = self._load()
        new_job = {
            "url": url,
            "status": status,
            "pdf_path": None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "details": None,
            "error_message": None
        }
        jobs.append(new_job)
        self._save(jobs)
        return True

    def update_job(self, url, status=None, pdf_path=None, details=None, error_message=None):
        """
        Updates an existing job's status and metadata.

        Args:
            url (str): The unique URL of the job to update.
            status (str, optional): New processing status.
            pdf_path (str, optional): Local path to the generated resume PDF.
            details (str, optional): Extracted job description snippet.
            error_message (str, optional): Error details if processing failed.

        Returns:
            bool: True if the job was found and updated, False otherwise.
        """
        jobs = self._load()
        updated = False
        for job in jobs:
            if job['url'] == url:
                if status: job['status'] = status
                if pdf_path: job['pdf_path'] = pdf_path
                if details: job['details'] = str(details)
                
                # Update error message (allows clearing with empty string or None)
                if error_message is not None:
                     job['error_message'] = str(error_message) if error_message else None
                
                job['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        
        if updated:
            self._save(jobs)
        return updated

