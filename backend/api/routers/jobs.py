from fastapi import APIRouter, Depends, HTTPException
from api.services.domain_services import JobService
from api.dependencies import get_job_service
from api.schemas.models import Job, FeedURLOnly

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/")
def get_jobs(service: JobService = Depends(get_job_service)):
    return service.get_jobs()

@router.post("/retry")
def retry_job(payload: FeedURLOnly, service: JobService = Depends(get_job_service)):
    # Using FeedURLOnly for simple URL payload
    if service.retry_job(payload.url):
        return {"status": "retried", "url": payload.url}
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("/")
def add_job(payload: FeedURLOnly, service: JobService = Depends(get_job_service)):
    if service.add_job(payload.url):
        return {"status": "added", "url": payload.url}
    return {"status": "exists", "url": payload.url}

@router.delete("/")
def delete_job(url: str, service: JobService = Depends(get_job_service)):
    if service.delete_job(url):
        return {"status": "deleted", "url": url}
    raise HTTPException(status_code=404, detail="Job not found")
