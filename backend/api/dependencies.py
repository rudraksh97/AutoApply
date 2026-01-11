from api.repositories.json_repo import JsonJobRepository, JsonConfigRepository, JsonProfileRepository
from api.services.domain_services import JobService, FeedService, ProfileService

# Singleton instances (or per-request if stateful)
_job_repo = JsonJobRepository()
_config_repo = JsonConfigRepository()
_profile_repo = JsonProfileRepository()

def get_job_service() -> JobService:
    return JobService(_job_repo)

def get_feed_service() -> FeedService:
    return FeedService(_config_repo)

def get_profile_service() -> ProfileService:
    return ProfileService(_profile_repo)
