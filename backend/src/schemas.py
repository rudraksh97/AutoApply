from typing import List, Optional
from pydantic import BaseModel, Field

# =============================================================================
# ATS and Resume Tailoring
# =============================================================================

class JustificationDetail(BaseModel):
    """Detailed breakdown of ATS score justification."""
    keyword_match: str = Field(description="Analysis of matched and missing keywords")
    skill_depth: str = Field(description="Evaluation of skill proficiency and relevance")
    role_fit: str = Field(description="Assessment of overall fit for the role")
    experience_relevance: str = Field(description="Alignment of past experience")
    education_fit: str = Field(description="Alignment of education and certifications")
    parsing_quality: str = Field(description="Quality of content structure")


class ATSScoreOutput(BaseModel):
    """Output schema for ATS score calculation."""
    missing_keywords: List[str] = Field(description="Keywords in job but not resume")
    matched_keywords: List[str] = Field(description="Keywords in both job and resume")
    score: int = Field(description="ATS score from 0 to 100")
    justification: JustificationDetail = Field(description="Score breakdown")


class TailoredResumeOutput(BaseModel):
    """Output schema for resume tailoring."""
    final_score: int = Field(description="Simulated ATS score 0-100")
    new_latex_code: str = Field(description="Full optimized LaTeX code")
    summary: List[str] = Field(description="List of changes made")


# =============================================================================
# Resume Parser
# =============================================================================

class Basics(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""

class URLs(BaseModel):
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""

class Demographics(BaseModel):
    gender: str = ""
    race: str = ""
    nationality: str = ""
    veteran: str = ""
    disability: str = ""

class WorkAuth(BaseModel):
    authorized_in_us: bool = True
    requires_sponsorship: bool = False

class Education(BaseModel):
    degree: str = ""
    university: str = ""
    field_of_study: str = ""
    graduation_year: str = ""

class Experience(BaseModel):
    company: str = ""
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""

class ResumeParserOutput(BaseModel):
    """Output schema for resume parsing."""
    basics: Basics
    urls: URLs
    demographics: Demographics
    work_auth: WorkAuth
    skills: List[str]
    education: List[Education]
    experience: List[Experience]


# =============================================================================
# RSS Job Link Extraction
# =============================================================================

class RSSLinkExtractionOutput(BaseModel):
    """Output schema for RSS job link extraction."""
    job_url: Optional[str] = Field(description="The extracted job application URL or null if not found")
    company_name: Optional[str] = Field(description="Company name extracted from content")
    job_title: Optional[str] = Field(description="Job title extracted from content")
    location: Optional[str] = Field(description="Job location if mentioned")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    notes: Optional[str] = Field(description="Any relevant notes about extraction")


# =============================================================================
# Form Answer Generation
# =============================================================================

class FormAnswer(BaseModel):
    """A structured answer for a form field."""
    xpath: str = Field(description="The accurate xpath of the field as provided in the input")
    value: Optional[str] = Field(None, description="The generated value to fill into the field. Use null if skipping.")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    skip: bool = Field(False, description="Whether to skip filling this field")
    skip_reason: Optional[str] = Field(None, description="Reason for skipping if applicable")

class FormAnswers(BaseModel):
    """Collection of form answers."""
    answers: List[FormAnswer] = Field(..., description="List of answers for the provided form fields")
