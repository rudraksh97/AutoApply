from api.interfaces.repositories import JobRepository, ConfigRepository, ProfileRepository
from src.job_manager import JobManager
from src.config import ConfigManager
from typing import List

# Adapter Pattern: Adapting old Managers to new Repository Interfaces

class JsonJobRepository(JobRepository):
    def __init__(self):
        self._manager = JobManager()

    def get_all_jobs(self) -> List[dict]:
        return self._manager.get_all_jobs()
    
    def job_exists(self, url: str) -> bool:
        return self._manager.job_exists(url)
    
    def add_job(self, url: str, status: str = "Pending") -> bool:
        return self._manager.add_job(url, status)

    def update_job(self, url: str, status: str = None, pdf_path: str = None, details: str = None, error_message: str = None) -> bool:
        return self._manager.update_job(url, status, pdf_path, details, error_message)

    def delete_job(self, url: str) -> bool:
        return self._manager.delete_job(url)

    def mark_as_sent(self, url: str, sent: bool = True) -> bool:
        return self._manager.mark_as_sent(url, sent)

class JsonConfigRepository(ConfigRepository):
    def __init__(self):
        self._manager = ConfigManager()

    def get_feeds(self) -> List[dict]:
        return self._manager.get_feeds()
    
    def add_feed(self, url: str, name: str) -> bool:
        return self._manager.add_feed(url, name)
    
    def remove_feed(self, url: str) -> bool:
        return self._manager.remove_feed(url)

class JsonProfileRepository(ProfileRepository):
    def __init__(self):
        # Stubbed out for migration. This repository is no longer used
        # in favor of SqlProfileRepository.
        self._manager = None

    def get_profile(self, user_id: str) -> dict:
        return {}
    
    def save_profile(self, user_id: str, profile: dict) -> None:
        self._manager.save_profile(profile)

    def add_resume(self, user_id: str, resume_type: str, filename: str, path: str) -> str:
        return self._manager.add_resume(resume_type, filename, path)

    def delete_resume(self, user_id: str, resume_id: str) -> bool:
        return self._manager.delete_resume(resume_id)

    def set_current_resume(self, user_id: str, resume_id: str) -> bool:
        return self._manager.set_current_resume(resume_id)
