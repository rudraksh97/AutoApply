from pydantic import BaseModel
from typing import Optional, Dict, List

class Job(BaseModel):
    url: str
    status: str
    pdf_path: Optional[str] = None
    timestamp: str
    details: Optional[str] = None
    error_message: Optional[str] = None
    sent: Optional[bool] = False
    retry_count: Optional[int] = 0

class FeedURL(BaseModel):
    """Request model for adding a feed - requires both URL and name."""
    url: str
    name: str  # Mandatory distinct name for the feed

class FeedURLOnly(BaseModel):
    """Request model when only URL is needed (e.g., for polling or removal)."""
    url: str

class Feed(BaseModel):
    """RSS Feed with a mandatory distinct name."""
    url: str
    name: str

class ProfileBasics(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    location: str

class ProfileURLs(BaseModel):
    linkedin: str
    github: str
    portfolio: str

class ProfileDemographics(BaseModel):
    gender: str
    race: Optional[str] = "Prefer not to say"
    nationality: str
    veteran: str
    disability: str

class ProfileWorkAuth(BaseModel):
    authorized_in_us: bool
    requires_sponsorship: bool

class ProfileEducation(BaseModel):
    degree: str
    university: str
    field_of_study: str
    graduation_year: str

class ProfileExperience(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str
    description: str

class ResumeInfo(BaseModel):
    id: str
    filename: str
    path: str
    created_at: str

class ProfileData(BaseModel):
    basics: ProfileBasics
    urls: ProfileURLs
    demographics: ProfileDemographics
    work_auth: ProfileWorkAuth
    education: List[ProfileEducation]
    experience: List[ProfileExperience]
    skills: str = ""
    great_fit_pitch: str = ""
    cover_letter_template: str = ""
    why_us: str = ""
    challenging_project: str = ""
    # Legacy fields (kept for migration/safety)
    uploaded_pdf_path: Optional[str] = ""
    uploaded_pdf_filename: Optional[str] = ""
    uploaded_tex_path: Optional[str] = ""
    uploaded_tex_filename: Optional[str] = ""
    
    # Multi-resume support
    pdf_resumes: List[ResumeInfo] = []
    text_resumes: List[ResumeInfo] = []
    current_pdf_resume_id: Optional[str] = None
    current_text_resume_id: Optional[str] = None
    
    resume_generation_mode: Optional[str] = "ats_generated"
    use_uploaded_resume: Optional[bool] = False
    custom_template_filename: Optional[str] = ""
