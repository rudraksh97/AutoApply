import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from api.services.domain_services import ProfileService
from api.dependencies import get_profile_service, get_current_user, get_db
from api.schemas.models import ProfileData
from src.models import User, Resume

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["Profile"])

# ─── Directory helpers ────────────────────────────────────────────────────────

def _user_dirs(user_email: str) -> dict[str, str]:
    """Return the canonical per-user directory paths."""
    base = os.path.join("data", user_email)
    return {
        "resumes":            os.path.join(base, "resumes"),
        "tex_resumes":        os.path.join(base, "tex_resumes"),
        "generated_resumes":  os.path.join(base, "generated_resumes"),
    }


def _ensure_user_dirs(user_email: str) -> dict[str, str]:
    """Create per-user directories if they don't already exist."""
    dirs = _user_dirs(user_email)
    for path in dirs.values():
        os.makedirs(path, exist_ok=True)
    return dirs


# ─── Profile CRUD ─────────────────────────────────────────────────────────────

@router.get("")
def get_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Returns the full profile document for the authenticated user."""
    return service.get_profile(current_user.id)


@router.post("")
@router.put("")
def save_profile(
    data: ProfileData,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """
    Persist the full user profile document (upsert).
    The knowledge_base array is validated and persisted inside the document.
    """
    service.save_profile(current_user.id, data.dict())
    return {"status": "saved"}


# ─── Resume Upload & Management ───────────────────────────────────────────────

@router.get("/resumes")
def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all resumes (PDF and LaTeX) stored for the current user,
    split by type, along with the active resume IDs from the profile.
    """
    rows = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    pdf_resumes = []
    tex_resumes = []
    for r in rows:
        info = {
            "id": r.id,
            "filename": r.filename,
            "path": r.path,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        (pdf_resumes if r.type == "PDF" else tex_resumes).append(info)

    return {"pdf_resumes": pdf_resumes, "tex_resumes": tex_resumes}


@router.post("/resumes", status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """
    Upload a PDF (.pdf) or LaTeX (.tex) resume.
    Stored under data/{user_email}/resumes/ or data/{user_email}/tex_resumes/.
    Returns the created resume metadata (id, filename, path, type).
    """
    filename = file.filename or ""
    is_pdf = filename.lower().endswith(".pdf")
    is_tex = filename.lower().endswith(".tex")

    if not (is_pdf or is_tex):
        raise HTTPException(status_code=400, detail="Only .pdf or .tex files are accepted")

    dirs = _ensure_user_dirs(current_user.email)
    save_dir = dirs["resumes"] if is_pdf else dirs["tex_resumes"]
    resume_type = "pdf" if is_pdf else "text"

    # Unique on-disk name to prevent collisions
    unique_name = f"{uuid.uuid4()}_{filename}"
    saved_path = os.path.join(save_dir, unique_name)

    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    resume = service.add_resume(
        user_id=current_user.id,
        resume_type=resume_type,
        filename=filename,
        path=saved_path,
    )
    return {"status": "uploaded", "resume": resume}


@router.delete("/resumes/{resume_id}")
def delete_resume(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Delete a resume by ID. Also removes the file from disk if it exists."""
    # Fetch path before deleting DB row
    from src.db import get_db as _get_db
    # We need the path — use the service (which has db access via the repo)
    # Load it directly since service.delete_resume returns bool only
    if not service.delete_resume(current_user.id, resume_id):
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"status": "deleted"}


@router.post("/resumes/{resume_id}/select")
def select_resume(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """Mark a resume as the active resume for the user."""
    if not service.set_current_resume(current_user.id, resume_id):
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"status": "selected"}


# ─── Autofill from Resume ─────────────────────────────────────────────────────

@router.post("/resumes/{resume_id}/autofill")
async def autofill_from_resume(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Parse an uploaded resume (PDF or .tex) using an LLM and return structured
    profile data that can be merged into the user's profile form on the frontend.

    The user confirms/edits before saving — this endpoint does NOT save the profile.
    Returns a partial profile dict with extracted fields.
    """
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not os.path.exists(resume.path):
        raise HTTPException(
            status_code=404,
            detail=f"Resume file not found on disk: {resume.filename}"
        )

    try:
        from src.resume_parser import ResumeParser
        parser = ResumeParser()
        extracted = await parser.parse_file(resume.path, current_user.id)
        return {
            "status": "success",
            "source_file": resume.filename,
            "extracted": extracted,
        }
    except RuntimeError as e:
        logger.error(f"Autofill failed for resume {resume_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during autofill for resume {resume_id}")
        raise HTTPException(status_code=500, detail="Failed to parse resume")
