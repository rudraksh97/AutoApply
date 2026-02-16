from fastapi import APIRouter, Depends, HTTPException
# Trigger reload
from api.services.domain_services import ProfileService
from api.dependencies import get_profile_service
from api.schemas.models import ProfileData

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("")
def get_profile(service: ProfileService = Depends(get_profile_service)):
    return service.get_profile()

@router.post("")
def save_profile(data: ProfileData, service: ProfileService = Depends(get_profile_service)):
    service.save_profile(data.dict())
    return {"status": "saved"}

@router.delete("/resumes/{resume_id}")
def delete_resume(resume_id: str, service: ProfileService = Depends(get_profile_service)):
    success = service.delete_resume(resume_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"status": "deleted"}

@router.post("/resumes/{resume_id}/select")
def select_resume(resume_id: str, service: ProfileService = Depends(get_profile_service)):
    success = service.set_current_resume(resume_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"status": "selected"}
