from api.repositories.json_repo import JsonJobRepository, JsonConfigRepository, JsonProfileRepository
from api.services.domain_services import JobService, FeedService, ProfileService
from api.services.task_registry import WorkflowRegistry

# Singleton instances (or per-request if stateful)
_job_repo = JsonJobRepository()
_config_repo = JsonConfigRepository()
_profile_repo = JsonProfileRepository()
_task_registry = WorkflowRegistry()

def get_job_service() -> JobService:
    return JobService(_job_repo, _task_registry)

def get_feed_service() -> FeedService:
    return FeedService(_config_repo)

def get_profile_service() -> ProfileService:
    return ProfileService(_profile_repo)
