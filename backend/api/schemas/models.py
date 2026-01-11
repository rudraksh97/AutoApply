from pydantic import BaseModel
from typing import Optional, Dict, List

class Job(BaseModel):
    url: str
    status: str
    pdf_path: Optional[str] = None
    timestamp: str
    details: Optional[str] = None
    error_message: Optional[str] = None

class FeedURL(BaseModel):
    url: str

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

class ProfileData(BaseModel):
    basics: ProfileBasics
    urls: ProfileURLs
    demographics: ProfileDemographics
    work_auth: ProfileWorkAuth
    education: List[ProfileEducation]
    experience: List[ProfileExperience]
    great_fit_pitch: str = ""
    cover_letter_template: str = ""
    why_us: str = ""
    challenging_project: str = ""
    uploaded_resume_path: Optional[str] = ""
    uploaded_resume_filename: Optional[str] = ""
    use_uploaded_resume: Optional[bool] = False
    custom_template_filename: Optional[str] = ""
