from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.services.domain_services import JobService
from api.dependencies import get_job_service
from api.schemas.models import Job, FeedURLOnly

router = APIRouter(prefix="/jobs", tags=["Jobs"])

class MarkSentPayload(BaseModel):
    url: str
    sent: bool = True

@router.get("")
def get_jobs(service: JobService = Depends(get_job_service)):
    return service.get_jobs()

@router.post("/retry")
def retry_job(payload: FeedURLOnly, service: JobService = Depends(get_job_service)):
    from src.job_manager_state import JobManagerState
    
    # Validation: Job Manager must be running to retry
    if not JobManagerState.is_running():
        raise HTTPException(
            status_code=400,
            detail="Job Manager is stopped. Please start the Job Manager in Settings before retrying jobs."
        )

    # Using FeedURLOnly for simple URL payload
    if service.retry_job(payload.url):
        return {"status": "retried", "url": payload.url}
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("")
def add_job(payload: FeedURLOnly, service: JobService = Depends(get_job_service)):
    if service.add_job(payload.url):
        return {"status": "added", "url": payload.url}
    return {"status": "exists", "url": payload.url}

@router.post("/sent")
def mark_job_sent(payload: MarkSentPayload, service: JobService = Depends(get_job_service)):
    if service.mark_as_sent(payload.url, payload.sent):
        return {"status": "updated", "url": payload.url, "sent": payload.sent}
    raise HTTPException(status_code=404, detail="Job not found")

@router.delete("")
def delete_job(url: str, service: JobService = Depends(get_job_service)):
    if service.delete_job(url):
        return {"status": "deleted", "url": url}
    raise HTTPException(status_code=404, detail="Job not found")
