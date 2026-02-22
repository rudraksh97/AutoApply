"""
SqlProfileRepository — unified profile persistence via UserProfile JSONB document.

Design contract:
  - Single source of truth: the `user_profiles.data` JSON column.
  - Schema = profile.json shape (see DEFAULT_PROFILE below).
  - knowledge_base is a [{id, question, answer}] array inside the document.
  - Resumes (files) continue to use the Resume table (binary metadata only).
  - The legacy flat-column Profile table is NOT used by this repo.
"""

from sqlalchemy.orm import Session
from src.models import UserProfile, Resume
import uuid
from datetime import datetime
from typing import Optional


def _new_id() -> str:
    return str(uuid.uuid4())


DEFAULT_PROFILE: dict = {
    "basics": {
        "first_name": "", "last_name": "", "email": "", "phone": "", "location": ""
    },
    "urls": {
        "linkedin": "", "github": "", "portfolio": ""
    },
    "demographics": {
        "gender": "", "race": "Prefer not to say", "nationality": "",
        "veteran": "I am not a protected veteran", "disability": "I do not have a disability"
    },
    "work_auth": {
        "authorized_in_us": True, "requires_sponsorship": False
    },
    "education": [],
    "experience": [],
    "skills": "",
    "cover_letter_template": "",
    "knowledge_base": [],          # [{id, question, answer}] — fully user-defined
    "pdf_resumes": [],             # Populated from Resume table at read-time
    "text_resumes": [],            # Populated from Resume table at read-time
    "current_pdf_resume_id": None,
    "current_text_resume_id": None,
    "resume_generation_mode": "ats_generated",
    "use_uploaded_resume": False,
}

# Fields within the doc that are dynamically injected from the Resume table
# (not stored inside the JSONB doc itself)
_RESUME_FIELDS = {"pdf_resumes", "text_resumes"}


class SqlProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get_resumes(self, user_id: str) -> tuple[list, list]:
        """Return (pdf_resumes, text_resumes) from the Resume table."""
        rows = self.db.query(Resume).filter(Resume.user_id == user_id).all()
        pdf, txt = [], []
        for r in rows:
            info = {
                "id": r.id,
                "filename": r.filename,
                "path": r.path,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            (pdf if r.type == "PDF" else txt).append(info)
        return pdf, txt

    def _get_or_create_doc(self, user_id: str) -> tuple["UserProfile", dict]:
        """Return the UserProfile row and its data dict, creating if absent."""
        row = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not row:
            import copy
            doc = copy.deepcopy(DEFAULT_PROFILE)
            row = UserProfile(user_id=user_id, data=doc)
            self.db.add(row)
            self.db.flush()     # Assign row to session without committing yet
        return row, row.data

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_profile(self, user_id: str) -> dict:
        """
        Returns the full profile document for the user.
        Always injects current resume lists from the Resume table.
        """
        import copy
        row = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        doc = copy.deepcopy(row.data if row else DEFAULT_PROFILE)

        # Ensure all expected top-level keys exist (forward compat)
        for key, default in DEFAULT_PROFILE.items():
            if key not in doc:
                import copy as _copy
                doc[key] = _copy.deepcopy(default)

        # Inject live resume data — never stale from the doc
        pdf, txt = self._get_resumes(user_id)
        doc["pdf_resumes"] = pdf
        doc["text_resumes"] = txt
        return doc

    def save_profile(self, user_id: str, data: dict) -> None:
        """
        Persist the full profile document.
        Resume lists (pdf_resumes, text_resumes) are stripped — they live in the Resume table.
        knowledge_base is persisted as-is and must be a list of {id, question, answer} dicts.
        """
        row, _ = self._get_or_create_doc(user_id)

        # Strip fields managed elsewhere
        clean = {k: v for k, v in data.items() if k not in _RESUME_FIELDS}

        # Validate knowledge_base entries
        kb = clean.get("knowledge_base", [])
        validated_kb = []
        for entry in kb:
            if not isinstance(entry, dict):
                continue
            q = str(entry.get("question", "")).strip()
            a = str(entry.get("answer", "")).strip()
            if not q or not a:
                continue
            validated_kb.append({
                "id": entry.get("id") or _new_id(),
                "question": q,
                "answer": a,
            })
        clean["knowledge_base"] = validated_kb

        row.data = clean
        row.updated_at = datetime.utcnow()
        self.db.commit()

    def add_resume(self, user_id: str, resume_type: str, filename: str, path: str) -> dict:
        """
        Insert a new Resume row. Returns the created resume dict.
        resume_type: 'pdf' | 'text'
        """
        db_type = "PDF" if resume_type == "pdf" else "TXT"
        resume = Resume(
            id=_new_id(),
            user_id=user_id,
            filename=filename,
            path=path,
            type=db_type,
        )
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return {
            "id": resume.id, "filename": resume.filename,
            "path": resume.path, "type": resume_type,
            "created_at": resume.created_at.isoformat() if resume.created_at else "",
        }

    def delete_resume(self, user_id: str, resume_id: str) -> bool:
        resume = (
            self.db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == user_id)
            .first()
        )
        if not resume:
            return False
        self.db.delete(resume)
        self.db.commit()
        return True

    def set_current_resume(self, user_id: str, resume_id: str) -> bool:
        """Set the active resume ID in the profile document."""
        resume = (
            self.db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == user_id)
            .first()
        )
        if not resume:
            return False

        row, doc = self._get_or_create_doc(user_id)
        if resume.type == "PDF":
            doc["current_pdf_resume_id"] = resume_id
        else:
            doc["current_text_resume_id"] = resume_id
        row.data = doc
        row.updated_at = datetime.utcnow()
        self.db.commit()
        return True
