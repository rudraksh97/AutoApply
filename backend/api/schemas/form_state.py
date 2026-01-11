"""
FormState and ApplicationDraft models for the draft-first workflow.

These models represent the source of truth for application data,
supporting versioning, persistence, and cross-session portability.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class DraftStatus(str, Enum):
    """Lifecycle states for an application draft."""
    JOB_FOUND = "job_found"
    EXTRACTED = "extracted"
    PREFILLED = "prefilled"
    DRAFT_SAVED = "draft_saved"
    USER_OPENED = "user_opened"


class FieldType(str, Enum):
    """Supported form field types."""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FILE = "file"
    TEXTAREA = "textarea"
    HIDDEN = "hidden"


class FieldState(BaseModel):
    """
    Represents the state of a single form field.
    
    Attributes:
        field_id: Unique identifier (CSS selector, name, or stable identifier)
        field_type: The type of form input
        label: Human-readable label for the field
        value: Current value (None if empty)
        confidence: How confident the system is in this value (0.0 to 1.0)
        user_edited: Whether the user has manually modified this field
        required: Whether this field is required
    """
    field_id: str
    field_type: FieldType = FieldType.TEXT
    label: Optional[str] = None
    value: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    user_edited: bool = False
    required: bool = False


class FormState(BaseModel):
    """
    Represents the complete state of a job application form.
    
    This is the source of truth for form data and is:
    - Fully serializable
    - Versioned for compatibility
    - Independent of browser session
    
    Attributes:
        version: Schema version for forward compatibility
        job_url: The URL of the job application
        page_index: Current page for multi-page forms (0-indexed)
        fields: List of all captured form fields
        extracted_at: When the form state was first captured
        last_modified: When the form state was last updated
    """
    version: str = "1.0"
    job_url: str
    page_index: int = 0
    fields: List[FieldState] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    
    def get_field(self, field_id: str) -> Optional[FieldState]:
        """Retrieve a field by its ID."""
        for field in self.fields:
            if field.field_id == field_id:
                return field
        return None
    
    def update_field(self, field_id: str, value: str, user_edited: bool = False) -> bool:
        """
        Update a field's value and mark as modified.
        
        Returns:
            True if field was found and updated, False otherwise.
        """
        field = self.get_field(field_id)
        if field:
            field.value = value
            field.user_edited = user_edited
            self.last_modified = datetime.utcnow()
            return True
        return False


class ApplicationDraft(BaseModel):
    """
    Represents a saved job application draft.
    
    A draft contains everything needed to resume or reopen an application:
    - Job metadata (URL, details)
    - Complete FormState
    - Resume path
    - Lifecycle status
    
    Drafts are portable across sessions and devices.
    
    Attributes:
        id: Unique identifier (UUID)
        job_url: URL of the job posting
        status: Current lifecycle status
        form_state: Complete form state (None before prefill)
        resume_path: Path to the resume file used
        job_details: Extracted job description
        created_at: When the draft was created
        updated_at: When the draft was last modified
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_url: str
    status: DraftStatus = DraftStatus.JOB_FOUND
    form_state: Optional[FormState] = None
    resume_path: Optional[str] = None
    job_details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def can_open(self) -> bool:
        """Check if the draft can be opened in a browser."""
        return self.status in (DraftStatus.PREFILLED, DraftStatus.DRAFT_SAVED, DraftStatus.USER_OPENED)
    
    def mark_opened(self) -> None:
        """Mark the draft as opened by the user."""
        self.status = DraftStatus.USER_OPENED
        self.updated_at = datetime.utcnow()


class DraftSummary(BaseModel):
    """
    Lightweight summary of a draft for listing endpoints.
    
    Does not include the full FormState to reduce payload size.
    """
    id: str
    job_url: str
    status: DraftStatus
    job_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    field_count: int = 0
    filled_field_count: int = 0
