from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel
from src.config import ConfigManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])

# =============================================================================
# Models
# =============================================================================

class AddLLMConfig(BaseModel):
    sdk_id: str
    name: str
    api_key: str
    plan_type: str = "free"
    daily_token_limit: Optional[int] = None

class UpdateLLMConfig(BaseModel):
    name: Optional[str] = None
    daily_token_limit: Optional[int] = None
    plan_type: Optional[str] = None

class LinkWorkflow(BaseModel):
    workflow_id: str
    llm_config_id: str

# =============================================================================
# Initialization Check (Frontend Helper)
# =============================================================================

@router.get("/init-status")
def get_init_status():
    """Checks if the system has at least one valid LLM configured."""
    cm = ConfigManager()
    configs = cm.get_user_configs()
    return {"configured": len(configs) > 0, "count": len(configs)}

# =============================================================================
# SDK Definitions (Static Options)
# =============================================================================

@router.get("/sdks")
def get_available_sdks():
    """Returns the list of supported LLM SDKs (from llms.json)."""
    cm = ConfigManager()
    return cm.get_sdk_definitions()

# =============================================================================
# LLM Inventory (User Configured Keys)
# =============================================================================

@router.get("/llm-inventory")
def get_llm_inventory():
    """Returns all configured LLM keys with usage stats."""
    cm = ConfigManager()
    configs = cm.get_user_configs()
    
    # Mask API keys for security
    masked = []
    for c in configs:
        m = c.copy()
        if m.get("api_key"):
            key = m["api_key"]
            if len(key) > 8:
                m["api_key"] = key[:4] + "..." + key[-4:]
            else:
                m["api_key"] = "****"
        masked.append(m)
    return masked

@router.post("/llm-inventory")
def add_llm_config(payload: AddLLMConfig):
    """Adds a new LLM configuration."""
    cm = ConfigManager()
    try:
        new_config = cm.add_user_config(
            sdk_id=payload.sdk_id,
            name=payload.name,
            api_key=payload.api_key,
            plan_type=payload.plan_type,
            daily_limit=payload.daily_token_limit
        )
        return {"status": "success", "config": new_config}
    except Exception as e:
        logger.error(f"Error adding LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/llm-inventory/{config_id}")
def remove_llm_config(config_id: str):
    """Removes an LLM configuration."""
    cm = ConfigManager()
    if cm.remove_user_config(config_id):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Config not found")

@router.patch("/llm-inventory/{config_id}")
def update_llm_config(config_id: str, payload: UpdateLLMConfig):
    """Updates an LLM configuration (name, limit, plan)."""
    cm = ConfigManager()
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        return {"status": "no_changes"}
    
    if cm.update_user_config(config_id, updates):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Config not found")

# =============================================================================
# Workflows & Linking
# =============================================================================

@router.get("/workflows")
def get_workflows():
    """Returns available workflow steps."""
    cm = ConfigManager()
    return cm.get_workflows()

@router.get("/workflow-links")
def get_workflow_links():
    """Returns current mappings between workflows and LLMs."""
    cm = ConfigManager()
    return cm.get_workflow_links()

@router.post("/workflow-links")
def link_workflow(payload: LinkWorkflow):
    """Links an LLM config to a workflow step."""
    cm = ConfigManager()
    cm.link_llm_to_workflow(payload.workflow_id, payload.llm_config_id)
    return {"status": "success"}

@router.delete("/workflow-links")
def unlink_workflow(payload: LinkWorkflow):
    """Unlinks an LLM config from a workflow step."""
    cm = ConfigManager()
    cm.unlink_llm_from_workflow(payload.workflow_id, payload.llm_config_id)
    return {"status": "success"}

# =============================================================================
# Legacy / Other
# =============================================================================

@router.get("/ats-prompts")
def get_ats_prompts():
    """Retrieves custom ATS prompts."""
    cm = ConfigManager()
    return cm.get_ats_prompts()

@router.post("/ats-prompts")
def set_ats_prompts(prompts: dict):
    """Updates custom ATS prompts."""
    try:
        cm = ConfigManager()
        cm.set_ats_prompts(prompts)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

