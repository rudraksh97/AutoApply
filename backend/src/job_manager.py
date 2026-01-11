import json
import os
from datetime import datetime

JOBS_FILE = "data/jobs.json"

class JobManager:
    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(JOBS_FILE):
            with open(JOBS_FILE, 'w') as f:
                json.dump([], f)

    def _load(self):
        try:
            with open(JOBS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, data):
        with open(JOBS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def get_all_jobs(self):
        return self._load()

    def job_exists(self, url):
        jobs = self._load()
        return any(job['url'] == url for job in jobs)

    def add_job(self, url, status="Pending"):
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
        jobs = self._load()
        updated = False
        for job in jobs:
            if job['url'] == url:
                if status: job['status'] = status
                if pdf_path: job['pdf_path'] = pdf_path
                if details: job['details'] = str(details)
                # If error_message is explicitly passed as "" or None (to clear it), we set it.
                # But to avoid accidental clearing if not passed, we check if it's in locals?
                # Actually for retry we want to clear it.
                # Let's say if it's passed, update it.
                if error_message is not None:
                     job['error_message'] = str(error_message) if error_message else None
                
                job['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        
        if updated:
            self._save(jobs)
        return updated
