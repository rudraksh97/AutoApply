from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.services.domain_services import JobService
from api.dependencies import get_job_service, get_current_user
from api.schemas.models import Job, FeedURLOnly
from src.models import User

router = APIRouter(prefix="/jobs", tags=["Jobs"])

class MarkSentPayload(BaseModel):
    url: str
    sent: bool = True

@router.get("")
def get_jobs(
    service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user)
):
    return service.get_jobs(current_user.id)

@router.post("/retry")
def retry_job(
    payload: FeedURLOnly, 
    service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user)
):
    from src.job_manager_state import JobManagerState
    
    # Validation: Job Manager must be running to retry
    if not JobManagerState.is_running():
        raise HTTPException(
            status_code=400,
            detail="Job Manager is stopped. Please start the Job Manager in Settings before retrying jobs."
        )

    if service.retry_job(payload.url, current_user.id):
        return {"status": "retried", "url": payload.url}
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("")
def add_job(
    payload: FeedURLOnly, 
    service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user)
):
    if service.add_job(payload.url, current_user.id):
        return {"status": "added", "url": payload.url}
    return {"status": "exists", "url": payload.url}

@router.post("/sent")
def mark_job_sent(
    payload: MarkSentPayload, 
    service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user)
):
    if service.mark_as_sent(payload.url, current_user.id, payload.sent):
        return {"status": "updated", "url": payload.url, "sent": payload.sent}
    raise HTTPException(status_code=404, detail="Job not found")

@router.delete("")
def delete_job(
    url: str, 
    service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user)
):
    if service.delete_job(url, current_user.id):
        return {"status": "deleted", "url": url}
    raise HTTPException(status_code=404, detail="Job not found")
