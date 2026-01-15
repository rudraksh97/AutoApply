from typing import List, Protocol, Optional
from api.schemas.models import Job, ProfileData

class JobRepository(Protocol):
    def get_all_jobs(self) -> List[dict]:
        ...
    
    def job_exists(self, url: str) -> bool:
        ...
    
    def add_job(self, url: str, status: str = "Pending") -> bool:
        ...

    def update_job(self, url: str, status: str = None, pdf_path: str = None, details: str = None, error_message: str = None) -> bool:
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
    def get_profile(self) -> dict:
        ...
    
    def save_profile(self, profile: dict) -> None:
        ...

    def add_resume(self, resume_type: str, filename: str, path: str) -> str:
        ...

    def delete_resume(self, resume_id: str) -> bool:
        ...

    def set_current_resume(self, resume_id: str) -> bool:
        ...
