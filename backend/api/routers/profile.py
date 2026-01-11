from fastapi import APIRouter, Depends, HTTPException
# Trigger reload
from api.services.domain_services import ProfileService
from api.dependencies import get_profile_service
from api.schemas.models import ProfileData

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("/")
def get_profile(service: ProfileService = Depends(get_profile_service)):
    return service.get_profile()

@router.post("/")
def save_profile(data: ProfileData, service: ProfileService = Depends(get_profile_service)):
    service.save_profile(data.dict())
    return {"status": "saved"}
