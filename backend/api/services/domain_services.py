from api.interfaces.repositories import JobRepository, ConfigRepository, ProfileRepository
from api.schemas.models import FeedURL, ProfileData

class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def get_jobs(self):
        jobs = self.repository.get_all_jobs()
        # Business Logic: Sort by timestamp 
        jobs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jobs

    def retry_job(self, url: str):
        if self.repository.job_exists(url):
            self.repository.update_job(url, status="Pending", error_message="")
            return True
        return False

    def add_job(self, url: str):
        if not self.repository.job_exists(url):
            self.repository.add_job(url, status="Pending")
            return True
        return False

    def delete_job(self, url: str):
        return self.repository.delete_job(url)

class FeedService:
    def __init__(self, repository: ConfigRepository):
        self.repository = repository

    def get_feeds(self):
        return self.repository.get_feeds()

    def add_feed(self, url: str, name: str):
        return self.repository.add_feed(url, name)

    def remove_feed(self, url: str):
        return self.repository.remove_feed(url)

class ProfileService:
    def __init__(self, repository: ProfileRepository):
        self.repository = repository

    def get_profile(self):
        return self.repository.get_profile()

    def save_profile(self, profile: dict):
        self.repository.save_profile(profile)
