"""
User profile management for the AutoApply application.

This module handles storage of personal details, work authorization,
education history, and resume management.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional


# =============================================================================
# Constants
# =============================================================================

PROFILE_FILE = "data/profile.json"

DEFAULT_PROFILE = {
    "basics": {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "location": ""
    },
    "urls": {
        "linkedin": "",
        "github": "",
        "portfolio": ""
    },
    "demographics": {
        "gender": "Prefer not to say",
        "race": "Prefer not to say",
        "nationality": "",
        "veteran": "I am not a protected veteran",
        "disability": "I do not have a disability"
    },
    "work_auth": {
        "authorized_in_us": True,
        "requires_sponsorship": False
    },
    "education": [],
    "experience": [],
    "skills": "",
    "great_fit_pitch": "",
    "cover_letter_template": "",
    "why_us": "",
    "challenging_project": "",
    "uploaded_pdf_path": "",
    "uploaded_pdf_filename": "",
    "uploaded_tex_path": "",
    "uploaded_tex_filename": "",
    "pdf_resumes": [],
    "text_resumes": [],
    "current_pdf_resume_id": None,
    "current_text_resume_id": None,
    "resume_generation_mode": "ats_generated",
    "use_uploaded_resume": False,
    "custom_template_filename": ""
}


# =============================================================================
# Profile Manager
# =============================================================================

class ProfileManager:
    """Manages the user's personal and professional profile data."""

    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        """Create data directory and profile file if they don't exist."""
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, 'w') as f:
                json.dump(DEFAULT_PROFILE, f, indent=2)

    # -------------------------------------------------------------------------
    # Core CRUD Operations
    # -------------------------------------------------------------------------

    def get_profile(self) -> dict:
        """Retrieve the user's profile data, merged with defaults."""
        try:
            with open(PROFILE_FILE, 'r') as f:
                data = json.load(f)
            return self._merge_with_defaults(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return DEFAULT_PROFILE.copy()

    def save_profile(self, profile_data: dict):
        """Save profile data with merge strategy to preserve existing keys."""
        existing = self.get_profile()

        for key, value in profile_data.items():
            if key in existing and isinstance(existing[key], dict) and isinstance(value, dict):
                existing[key].update(value)
            else:
                existing[key] = value

        with open(PROFILE_FILE, 'w') as f:
            json.dump(existing, f, indent=2)

    # -------------------------------------------------------------------------
    # Profile Merging and Migration
    # -------------------------------------------------------------------------

    def _merge_with_defaults(self, data: dict) -> dict:
        """Merge loaded data with defaults and apply migrations."""
        merged = DEFAULT_PROFILE.copy()

        for key, value in data.items():
            merged[key] = self._migrate_field(key, value, merged.get(key))

        self._migrate_resume_paths(data, merged)
        self._migrate_to_multi_resume(merged)

        return merged

    def _migrate_field(self, key: str, value, default):
        """Apply field-specific migrations."""
        # Education: convert dict to list
        if key == "education" and isinstance(value, dict):
            if not value.get("university"):
                return []
            return [value]

        # Resume mode: normalize terminology
        if key == "resume_generation_mode":
            mode_map = {
                "generate_from_default": "ats_generated",
                "generate_from_custom_tex": "ats_generated",
                "use_uploaded_pdf": "uploaded_pdf"
            }
            return mode_map.get(value, value)

        # Dict fields: merge with defaults
        if isinstance(default, dict) and isinstance(value, dict):
            merged_dict = default.copy()
            merged_dict.update(value)
            return merged_dict

        return value

    def _migrate_resume_paths(self, data: dict, merged: dict):
        """Migrate old uploaded_resume_path to new structure."""
        old_path = data.get("uploaded_resume_path")
        if not old_path or not os.path.exists(old_path):
            return

        if old_path.endswith(".pdf") and not merged.get("uploaded_pdf_path"):
            merged["uploaded_pdf_path"] = old_path
            merged["uploaded_pdf_filename"] = data.get(
                "uploaded_resume_filename", os.path.basename(old_path)
            )
        elif old_path.endswith(".tex") and not merged.get("uploaded_tex_path"):
            merged["uploaded_tex_path"] = old_path
            merged["uploaded_tex_filename"] = data.get(
                "uploaded_resume_filename", os.path.basename(old_path)
            )

        # Ensure filenames are populated
        if merged.get("uploaded_pdf_path") and not merged.get("uploaded_pdf_filename"):
            merged["uploaded_pdf_filename"] = os.path.basename(merged["uploaded_pdf_path"])
        if merged.get("uploaded_tex_path") and not merged.get("uploaded_tex_filename"):
            merged["uploaded_tex_filename"] = os.path.basename(merged["uploaded_tex_path"])

    def _migrate_to_multi_resume(self, merged: dict):
        """Migrate single resume fields to multi-resume structure."""
        # Migrate PDF
        if merged.get("uploaded_pdf_path") and not merged.get("pdf_resumes"):
            resume_id = str(uuid.uuid4())
            merged["pdf_resumes"] = [{
                "id": resume_id,
                "filename": merged.get("uploaded_pdf_filename", "Resume.pdf"),
                "path": merged["uploaded_pdf_path"],
                "created_at": datetime.utcnow().isoformat()
            }]
            merged["current_pdf_resume_id"] = resume_id

        # Migrate TeX
        if merged.get("uploaded_tex_path") and not merged.get("text_resumes"):
            resume_id = str(uuid.uuid4())
            merged["text_resumes"] = [{
                "id": resume_id,
                "filename": merged.get("uploaded_tex_filename", "Resume.tex"),
                "path": merged["uploaded_tex_path"],
                "created_at": datetime.utcnow().isoformat()
            }]
            merged["current_text_resume_id"] = resume_id

    # -------------------------------------------------------------------------
    # Resume Data Import
    # -------------------------------------------------------------------------

    def update_from_resume_data(self, parsed_data: dict, resume_path: str = None):
        """Update profile with data parsed from a resume."""
        profile = self.get_profile()

        if parsed_data.get("basics"):
            profile["basics"].update(parsed_data["basics"])
        if parsed_data.get("urls"):
            profile["urls"].update(parsed_data["urls"])
        if parsed_data.get("education"):
            profile["education"] = parsed_data["education"]
        if parsed_data.get("experience"):
            profile["experience"] = parsed_data["experience"]
        if parsed_data.get("skills"):
            skills = parsed_data["skills"]
            profile["skills"] = ", ".join(skills) if isinstance(skills, list) else str(skills)

        if resume_path:
            profile["uploaded_resume_path"] = resume_path

        self.save_profile(profile)

    # -------------------------------------------------------------------------
    # Text Export
    # -------------------------------------------------------------------------

    def get_profile_as_text(self) -> str:
        """Return profile as formatted text for LLM consumption."""
        p = self.get_profile()

        edu_text = self._format_education(p.get('education', []))
        exp_text = self._format_experience(p.get('experience', []))

        return f"""
=== PERSONAL INFORMATION ===
first_name: {p['basics']['first_name']}
last_name: {p['basics']['last_name']}
full_name: {p['basics']['first_name']} {p['basics']['last_name']}
email: {p['basics']['email']}
phone: {p['basics']['phone']}
location: {p['basics']['location']}

=== ONLINE PROFILES ===
linkedin: {p['urls']['linkedin']}
github: {p['urls']['github']}
portfolio: {p['urls']['portfolio']}

=== DEMOGRAPHICS (EEO/Voluntary Disclosure) ===
gender: {p['demographics']['gender']}
race: {p['demographics'].get('race', 'Prefer not to say')}
nationality: {p['demographics']['nationality']}
veteran_status: {p['demographics']['veteran']}
disability_status: {p['demographics']['disability']}

=== WORK AUTHORIZATION ===
authorized_to_work: {'Yes' if p['work_auth']['authorized_in_us'] else 'No'}
requires_sponsorship: {'Yes' if p['work_auth']['requires_sponsorship'] else 'No'}

=== SKILLS ===
skills: {p.get('skills', '(Not provided)')}

=== EXPERIENCE ===
{exp_text}
=== EDUCATION ===
{edu_text}
=== APPLICATION RESPONSES ===
great_fit_pitch: {p.get('great_fit_pitch', '(Not provided)')}

why_us: {p.get('why_us', '(Not provided)')}

challenging_project: {p.get('challenging_project', '(Not provided)')}
""".strip()

    def _format_education(self, education: list) -> str:
        """Format education list as text."""
        if not education:
            return "  (No education entries)\n"

        lines = []
        for edu in education:
            degree = edu.get('degree', '')
            field = edu.get('field_of_study', '')
            uni = edu.get('university', '')
            year = edu.get('graduation_year', '')
            lines.append(f"  - {degree} in {field} from {uni} ({year})")
        return "\n".join(lines) + "\n"

    def _format_experience(self, experience: list) -> str:
        """Format experience list as text."""
        if not experience:
            return "  (No experience entries)\n"

        lines = []
        for exp in experience:
            role = exp.get('role', '')
            company = exp.get('company', '')
            start = exp.get('start_date', '')
            end = exp.get('end_date', '')
            desc = exp.get('description', '')
            lines.append(f"  - {role} at {company} ({start} - {end})")
            if desc:
                lines.append(f"    {desc}")
        return "\n".join(lines) + "\n"

    # -------------------------------------------------------------------------
    # Resume Management
    # -------------------------------------------------------------------------

    def add_resume(self, resume_type: str, filename: str, path: str) -> str:
        """Add a new resume and make it current. Returns the resume ID."""
        profile = self.get_profile()
        resume_id = str(uuid.uuid4())

        resume_info = {
            "id": resume_id,
            "filename": filename,
            "path": path,
            "created_at": datetime.utcnow().isoformat()
        }

        if resume_type == "pdf":
            profile["pdf_resumes"].append(resume_info)
            profile["current_pdf_resume_id"] = resume_id
            profile["uploaded_pdf_path"] = path
            profile["uploaded_pdf_filename"] = filename
        else:
            profile["text_resumes"].append(resume_info)
            profile["current_text_resume_id"] = resume_id
            profile["uploaded_tex_path"] = path
            profile["uploaded_tex_filename"] = filename

        self.save_profile(profile)
        return resume_id

    def delete_resume(self, resume_id: str) -> bool:
        """Delete a resume by ID. Returns True if found and deleted."""
        profile = self.get_profile()

        # Try PDF resumes
        if self._delete_from_list(profile, "pdf_resumes", "current_pdf_resume_id",
                                   "uploaded_pdf_path", resume_id):
            self.save_profile(profile)
            return True

        # Try text resumes
        if self._delete_from_list(profile, "text_resumes", "current_text_resume_id",
                                   "uploaded_tex_path", resume_id):
            self.save_profile(profile)
            return True

        return False

    def _delete_from_list(
        self, profile: dict, list_key: str, current_key: str,
        path_key: str, resume_id: str
    ) -> bool:
        """Helper to delete resume from a specific list."""
        resumes = profile.get(list_key, [])

        for i, r in enumerate(resumes):
            if r["id"] == resume_id:
                resumes.pop(i)

                if profile[current_key] == resume_id:
                    if resumes:
                        profile[current_key] = resumes[0]["id"]
                        profile[path_key] = resumes[0]["path"]
                    else:
                        profile[current_key] = None
                        profile[path_key] = ""
                return True

        return False

    def set_current_resume(self, resume_id: str) -> bool:
        """Set a resume as current by ID. Returns True if found."""
        profile = self.get_profile()

        # Try PDF resumes
        for r in profile.get("pdf_resumes", []):
            if r["id"] == resume_id:
                profile["current_pdf_resume_id"] = resume_id
                profile["uploaded_pdf_path"] = r["path"]
                profile["uploaded_pdf_filename"] = r["filename"]
                self.save_profile(profile)
                return True

        # Try text resumes
        for r in profile.get("text_resumes", []):
            if r["id"] == resume_id:
                profile["current_text_resume_id"] = resume_id
                profile["uploaded_tex_path"] = r["path"]
                profile["uploaded_tex_filename"] = r["filename"]
                self.save_profile(profile)
                return True

        return False

    def get_current_resume_path(self, resume_type: str = "pdf") -> Optional[str]:
        """Get the path of the currently selected resume."""
        profile = self.get_profile()

        if resume_type == "pdf":
            current_id = profile.get("current_pdf_resume_id")
            resumes = profile.get("pdf_resumes", [])
            fallback = profile.get("uploaded_pdf_path")
        else:
            current_id = profile.get("current_text_resume_id")
            resumes = profile.get("text_resumes", [])
            fallback = profile.get("uploaded_tex_path")

        for r in resumes:
            if r["id"] == current_id:
                return r["path"]

        return fallback
