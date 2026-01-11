from fastapi import APIRouter, Depends, HTTPException
from api.services.domain_services import JobService
from api.dependencies import get_job_service
from api.schemas.models import Job, FeedURL

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/")
def get_jobs(service: JobService = Depends(get_job_service)):
    return service.get_jobs()

@router.post("/retry")
def retry_job(payload: FeedURL, service: JobService = Depends(get_job_service)):
    # Using FeedURL for simple URL payload to avoid extra model
    if service.retry_job(payload.url):
        return {"status": "retried", "url": payload.url}
    raise HTTPException(status_code=404, detail="Job not found")
