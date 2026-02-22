from fastapi import APIRouter, HTTPException, Body, Depends, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import logging

from src.config import ConfigManager
from api.dependencies import get_db, get_current_user
from src.models import Settings, User
from api.repositories.sql_repo import SqlProfileRepository
from api.services.domain_services import ProfileService

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
# SDK Definitions (Static Options — from llms.json)
# =============================================================================

@router.get("/sdks")
def get_available_sdks():
    """Returns the list of supported LLM SDKs."""
    cm = ConfigManager()
    return cm.get_sdk_definitions()

# =============================================================================
# LLM Inventory (User Configured Keys — DB-backed, per-user)
# =============================================================================

@router.get("/llm-inventory")
def get_llm_inventory(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the current user's configured LLM API keys.
    API keys are masked in the response.
    """
    from src.models import LLMConfig
    configs = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).all()
    masked = []
    for c in configs:
        row = {
            "id": c.id, "sdk_id": c.sdk_id, "name": c.name,
            "plan_type": c.plan_type, "daily_token_limit": c.daily_token_limit,
            "tokens_used_today": c.tokens_used_today or 0,
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
        }
        key = c.api_key or ""
        row["api_key"] = (key[:4] + "..." + key[-4:]) if len(key) > 8 else "****"
        masked.append(row)
    return masked

@router.get("/init-status")
def get_init_status(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns whether the current user has at least one LLM config."""
    from src.models import LLMConfig
    count = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).count()
    return {"configured": count > 0, "count": count}

@router.post("/llm-inventory")
def add_llm_config(
    payload: AddLLMConfig,
    user=Depends(get_current_user)
):
    """Adds a new LLM configuration for the current user."""
    cm = ConfigManager()
    try:
        new_config = cm.add_user_config(
            sdk_id=payload.sdk_id,
            name=payload.name,
            api_key=payload.api_key,
            plan_type=payload.plan_type,
            daily_limit=payload.daily_token_limit,
            user_id=user.id,
        )
        # Mask key before returning
        key = new_config.get("api_key", "")
        new_config["api_key"] = (key[:4] + "..." + key[-4:]) if len(key) > 8 else "****"
        return {"status": "success", "config": new_config}
    except Exception as e:
        logger.error(f"Error adding LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/llm-inventory/{config_id}")
def remove_llm_config(
    config_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Removes the user's LLM configuration. Admin can remove any config."""
    from src.models import LLMConfig
    q = db.query(LLMConfig).filter(LLMConfig.id == config_id)
    if "admin" not in user.roles:
        q = q.filter(LLMConfig.user_id == user.id)
    cfg = q.first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(cfg)
    db.commit()
    return {"status": "success"}

@router.patch("/llm-inventory/{config_id}")
def update_llm_config(
    config_id: str,
    payload: UpdateLLMConfig,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates an LLM configuration (name, limit, plan)."""
    from src.models import LLMConfig
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        return {"status": "no_changes"}
    q = db.query(LLMConfig).filter(LLMConfig.id == config_id)
    if "admin" not in user.roles:
        q = q.filter(LLMConfig.user_id == user.id)
    cfg = q.first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    for k, v in updates.items():
        setattr(cfg, k, v)
    db.commit()
    return {"status": "success"}

# =============================================================================
# Workflows & Linking (DB-backed, per-user)
# =============================================================================

@router.get("/workflows")
def get_workflows(
    db: Session = Depends(get_db)
):
    """
    Returns the global catalogue of workflow step definitions.
    Served from DB (seeded from workflows.json on startup).
    """
    from src.models import WorkflowStep
    steps = db.query(WorkflowStep).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "required_capabilities": s.required_capabilities or [],
        }
        for s in steps
    ]

@router.get("/workflow-links")
def get_workflow_links(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns this user's WorkflowStep → LLM configuration assignments.
    Scoped strictly to the authenticated user.
    """
    from src.models import WorkflowLLMLink
    links = db.query(WorkflowLLMLink).filter(
        WorkflowLLMLink.user_id == user.id
    ).all()
    return [
        {
            "id": link.id,
            "workflow_id": link.workflow_id,
            "llm_config_id": link.llm_config_id,
        }
        for link in links
    ]

@router.post("/workflow-links")
def link_workflow(
    payload: LinkWorkflow,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign an LLM config to a workflow step for the current user.
    Upsert semantics: if a link for (user, workflow) already exists,
    update the llm_config_id instead of creating a duplicate.
    """
    from src.models import WorkflowLLMLink, WorkflowStep

    # Validate the workflow step exists
    if not db.query(WorkflowStep).filter(WorkflowStep.id == payload.workflow_id).first():
        raise HTTPException(status_code=404, detail=f"Workflow step '{payload.workflow_id}' not found")

    existing = db.query(WorkflowLLMLink).filter(
        WorkflowLLMLink.user_id == user.id,
        WorkflowLLMLink.workflow_id == payload.workflow_id
    ).first()

    if existing:
        existing.llm_config_id = payload.llm_config_id
    else:
        db.add(WorkflowLLMLink(
            user_id=user.id,
            workflow_id=payload.workflow_id,
            llm_config_id=payload.llm_config_id
        ))
    db.commit()
    return {"status": "success"}

@router.delete("/workflow-links")
def unlink_workflow(
    payload: LinkWorkflow,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove the LLM assignment for a workflow step for the current user.
    Returns 404 if the link doesn't exist.
    """
    from src.models import WorkflowLLMLink
    link = db.query(WorkflowLLMLink).filter(
        WorkflowLLMLink.user_id == user.id,
        WorkflowLLMLink.workflow_id == payload.workflow_id,
        WorkflowLLMLink.llm_config_id == payload.llm_config_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Workflow link not found")
    db.delete(link)
    db.commit()
    return {"status": "success"}

# -----------------------------------------------------------------------------
# Job Manager Control
# -----------------------------------------------------------------------------

@router.get("/job-manager/status")
def get_job_manager_status():
    from src.job_manager_state import JobManagerState
    return JobManagerState.get_status()

@router.post("/job-manager/start")
def start_job_manager():
    from src.job_manager_state import JobManagerState
    from src.config import ConfigManager

    cm = ConfigManager()
    links = cm.get_workflow_links()
    
    # Validation: Ensure all 4 required steps have at least one LLM
    required_steps = [
        "step_browser_automation",
        "step_ats_scoring",
        "step_resume_tailoring",
        "step_form_answering"
    ]
    
    missing_steps = []
    for step in required_steps:
        # Check if any link exists for this step
        if not any(link["workflow_id"] == step for link in links):
            missing_steps.append(step)
            
    if missing_steps:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot start: Missing LLM for steps: {', '.join(missing_steps)}"
        )

    JobManagerState.set_running(True)
    return {"status": "started"}

@router.post("/job-manager/stop")
def stop_job_manager():
    from src.job_manager_state import JobManagerState
    JobManagerState.set_running(False)
    return {"status": "stopped"}

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

@router.get("/preferences")
def get_preferences(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences like global feed visibility."""
    settings = db.query(Settings).filter(Settings.user_id == user.id).first()
    if not settings:
        # Create default
        settings = Settings(user_id=user.id, include_global_feeds=True)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return {"include_global_feeds": settings.include_global_feeds}

class PreferencesUpdate(BaseModel):
    include_global_feeds: bool

@router.put("/preferences")
def update_preferences(
    prefs: PreferencesUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences."""
    settings = db.query(Settings).filter(Settings.user_id == user.id).first()
    if not settings:
        settings = Settings(user_id=user.id, include_global_feeds=prefs.include_global_feeds)
        db.add(settings)
    else:
        settings.include_global_feeds = prefs.include_global_feeds
    
    db.commit()
    return {"status": "success", "include_global_feeds": settings.include_global_feeds}


# =============================================================================
# Upload & Parse Endpoints (Moved from server.py)
# =============================================================================

@router.post("/upload-template")
async def upload_template(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a LaTeX resume template."""
    if not file.filename.endswith(".tex"):
        raise HTTPException(status_code=400, detail="Only .tex files allowed")

    # Ensure directory
    save_dir = "data/resumes/templates"
    os.makedirs(save_dir, exist_ok=True)
    save_path = f"{save_dir}/{file.filename}"
    content = await file.read()

    with open(save_path, "wb") as f:
        f.write(content)

    # Use ProfileService
    repo = SqlProfileRepository(db)
    service = ProfileService(repo)
    
    resume_id = service.add_resume(current_user.id, "text", file.filename, save_path)

    profile = service.get_profile(current_user.id)
    profile["custom_template_filename"] = file.filename
    service.save_profile(current_user.id, profile)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "path": save_path,
        "resume_id": resume_id
    }


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a resume (PDF or LaTeX)."""
    is_pdf = file.filename.endswith(".pdf")
    is_tex = file.filename.endswith(".tex")

    if not (is_pdf or is_tex):
        raise HTTPException(status_code=400, detail="Only .pdf or .tex files allowed")

    save_dir = "data/resumes" if is_pdf else "data/resumes/templates"
    os.makedirs(save_dir, exist_ok=True)
    save_path = f"{save_dir}/{file.filename}"
    content = await file.read()

    with open(save_path, "wb") as f:
        f.write(content)

    repo = SqlProfileRepository(db)
    service = ProfileService(repo)
    
    resume_type = "pdf" if is_pdf else "text"
    resume_id = service.add_resume(current_user.id, resume_type, file.filename, save_path)

    profile = service.get_profile(current_user.id)
    if is_pdf:
        profile["resume_generation_mode"] = "uploaded_pdf"
        profile["uploaded_pdf_path"] = save_path
    else:
        profile["resume_generation_mode"] = "ats_generated"
        profile["custom_template_filename"] = file.filename
        profile["uploaded_tex_path"] = save_path

    service.save_profile(current_user.id, profile)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "path": save_path,
        "resume_id": resume_id
    }


@router.post("/parse-resume")
async def parse_resume(
    source: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Parse an uploaded resume to extract profile data."""
    from src.resume_parser import ResumeParser
    
    repo = SqlProfileRepository(db)
    service = ProfileService(repo)

    resume_type = "text" if source == "tex" else "pdf"
    profile = service.get_profile(current_user.id)
    
    def get_path(resumes_list, current_id, fallback_path):
         if not current_id: return fallback_path
         for r in resumes_list:
             if r["id"] == current_id:
                 return r["path"]
         return fallback_path
    
    file_path = None
    if resume_type == "pdf":
        file_path = get_path(profile.get("pdf_resumes", []), profile.get("current_pdf_resume_id"), profile.get("uploaded_pdf_path"))
    else:
        file_path = get_path(profile.get("text_resumes", []), profile.get("current_text_resume_id"), profile.get("uploaded_tex_path"))

    if not file_path or not os.path.exists(file_path):
        file_type = "LaTeX" if source == "tex" else "PDF"
        raise HTTPException(
            status_code=400,
            detail=f"No selected {file_type} resume found. Please upload and select one first."
        )

    try:
        parser = ResumeParser()
        parsed_data = await parser.parse_file(file_path, current_user.id)
        return parsed_data
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logging.error(f"Resume parsing error: {e}\nStack trace:\n{tb}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
