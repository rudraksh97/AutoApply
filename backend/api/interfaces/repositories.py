from typing import List, Protocol, Optional
from api.schemas.models import Job, ProfileData

class JobRepository(Protocol):
    def get_all_jobs(self, user_id: str = None) -> List[dict]:
        ...
    
    def job_exists(self, url: str) -> bool:
        ...
    
    def add_job(self, url: str, user_id: str, status: str = "Pending") -> bool:
        ...

    def update_job(self, url: str, user_id: str, status: str = None, pdf_path: str = None, details: str = None, error_message: str = None) -> bool:
        ...
    
    def delete_job(self, url: str, user_id: str) -> bool:
        ...
    
    def mark_as_sent(self, url: str, sent: bool = True, user_id: str = None) -> bool:
        ...

class ConfigRepository(Protocol):
    def get_feeds(self) -> List[dict]:
        """Returns list of feed objects with 'url' and 'name' fields."""
        ...
    
    def add_feed(self, url: str, name: str) -> bool:
        """Adds a feed with distinct name. Returns False if url or name already exists."""
        ...
    
    def remove_feed(self, url: str) -> bool:
        ...

class ProfileRepository(Protocol):
    def get_profile(self, user_id: str) -> dict:
        ...
    
    def save_profile(self, user_id: str, profile: dict) -> None:
        ...

    def add_resume(self, user_id: str, resume_type: str, filename: str, path: str) -> str:
        ...

    def delete_resume(self, user_id: str, resume_id: str) -> bool:
        ...

    def set_current_resume(self, user_id: str, resume_id: str) -> bool:
        ...
