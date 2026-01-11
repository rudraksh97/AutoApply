from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.config import ConfigManager

router = APIRouter(prefix="/settings", tags=["Settings"])

class APIKeyUpdate(BaseModel):
    key_name: str
    key_value: str

@router.get("/keys")
def get_key_status():
    """Returns which keys are configured (without revealing values)."""
    cm = ConfigManager()
    # Check for common keys
    keys = ["OPENROUTER_API_KEY"]
    status = []
    for k in keys:
        val = cm.get_api_key(k)
        status.append({
            "name": k,
            "configured": bool(val)
        })
    return status

@router.post("/keys")
def set_api_key(payload: APIKeyUpdate):
    """Securely updates an API key in the .env file."""
    try:
        cm = ConfigManager()
        cm.set_api_key(payload.key_name, payload.key_value)
        return {"status": "success", "message": f"Updated {payload.key_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
