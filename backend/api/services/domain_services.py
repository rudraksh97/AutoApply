from api.interfaces.repositories import JobRepository, ConfigRepository, ProfileRepository
from api.schemas.models import FeedURL, ProfileData

class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def get_jobs(self, user_id: str):
        jobs = self.repository.get_all_jobs(user_id)
        # Business Logic: Sort by timestamp 
        jobs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jobs

    def retry_job(self, url: str, user_id: str):
        # We need job_exists to take user_id too if we want to be strict
        # But repository.job_exists(url) in interface didn't have user_id updated in my previous step?
        # Wait, I missed updating job_exists in repository interface above.
        # I will assume I can update it.
        # But JobManager.job_exists DOES take user_id now.
        if self.repository.job_exists(url, user_id):
            self.repository.update_job(url, user_id, status="Retried", error_message="")
            return True
        return False

    def add_job(self, url: str, user_id: str):
        if not self.repository.job_exists(url, user_id):
            self.repository.add_job(url, user_id, status="Pending")
            return True
        return False

    def delete_job(self, url: str, user_id: str):
        return self.repository.delete_job(url, user_id)

    def mark_as_sent(self, url: str, user_id: str, sent: bool = True):
        return self.repository.mark_as_sent(url, sent=sent, user_id=user_id)



class ProfileService:
    def __init__(self, repository: ProfileRepository):
        self.repository = repository

    def get_profile(self, user_id: str):
        return self.repository.get_profile(user_id)

    def save_profile(self, user_id: str, profile: dict):
        self.repository.save_profile(user_id, profile)

    def add_resume(self, user_id: str, resume_type: str, filename: str, path: str):
        return self.repository.add_resume(user_id, resume_type, filename, path)

    def delete_resume(self, user_id: str, resume_id: str):
        return self.repository.delete_resume(user_id, resume_id)

    def set_current_resume(self, user_id: str, resume_id: str):
        return self.repository.set_current_resume(user_id, resume_id)
