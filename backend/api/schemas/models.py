from pydantic import BaseModel, validator
from typing import Optional, Dict, List, Any


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
    name: str


class FeedURLOnly(BaseModel):
    """Request model when only URL is needed (e.g., for polling or removal)."""
    url: str


class Feed(BaseModel):
    """RSS Feed with a mandatory distinct name."""
    url: str
    name: str


# =============================================================================
# Profile sub-models
# =============================================================================

class ProfileBasics(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""


class ProfileURLs(BaseModel):
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


class ProfileDemographics(BaseModel):
    gender: str = ""
    race: Optional[str] = "Prefer not to say"
    nationality: str = ""
    veteran: str = "I am not a protected veteran"
    disability: str = "I do not have a disability"


class ProfileWorkAuth(BaseModel):
    authorized_in_us: bool = True
    requires_sponsorship: bool = False


class ProfileEducation(BaseModel):
    degree: str = ""
    university: str = ""
    field_of_study: str = ""
    graduation_year: str = ""


class ProfileExperience(BaseModel):
    company: str = ""
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""


class KnowledgeBaseEntry(BaseModel):
    """A single dynamic Q&A entry in the user's knowledge base."""
    id: Optional[str] = None          # Generated server-side if absent
    question: str
    answer: str


class ResumeInfo(BaseModel):
    id: str
    filename: str
    path: str
    created_at: str = ""


class ProfileData(BaseModel):
    """
    Full profile document. Matches UserProfile.data schema exactly.
    Resume lists are read-only (injected from Resume table); they are
    stripped before persistence and should not be sent in save requests.
    """
    basics: ProfileBasics = ProfileBasics()
    urls: ProfileURLs = ProfileURLs()
    demographics: ProfileDemographics = ProfileDemographics()
    work_auth: ProfileWorkAuth = ProfileWorkAuth()
    education: List[ProfileEducation] = []
    experience: List[ProfileExperience] = []
    skills: str = ""
    cover_letter_template: str = ""

    # Dynamic Q&A knowledge base — fully user-defined
    knowledge_base: List[KnowledgeBaseEntry] = []

    # Resume preferences
    current_pdf_resume_id: Optional[str] = None
    current_text_resume_id: Optional[str] = None
    resume_generation_mode: Optional[str] = "ats_generated"
    use_uploaded_resume: Optional[bool] = False

    # Read-only: injected at response time, never persisted inside the JSON doc
    pdf_resumes: List[ResumeInfo] = []
    text_resumes: List[ResumeInfo] = []

    class Config:
        # Allow any extra fields from older profile documents to pass through
        # without validation errors during migration period
        extra = "allow"
