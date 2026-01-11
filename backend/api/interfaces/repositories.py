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
    def get_feeds(self) -> List[str]:
        ...
    
    def add_feed(self, url: str) -> bool:
        ...
    
    def remove_feed(self, url: str) -> bool:
        ...

class ProfileRepository(Protocol):
    def get_profile(self) -> dict:
        ...
    
    def save_profile(self, profile: dict) -> None:
        ...
