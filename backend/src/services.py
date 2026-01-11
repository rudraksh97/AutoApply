"""
Core service layer for the AutoApply application.

This module contains the business logic for orchestrating the draft-first
workflow, coordinating between storage, browser automation, and resume generation.

CRITICAL: This service NEVER submits applications. All operations result in
saved drafts that users can open and complete manually.
"""

import logging
from typing import Callable, Optional
from datetime import datetime
from src.interfaces import JobManagerProtocol, BrowserAgentProtocol, ResumeBuilderProtocol
from src.draft_manager import DraftManager
from api.schemas.form_state import FormState, FieldState, FieldType, DraftStatus
import os

# Preserving the constant from main.py for behavior compatibility
# In a future refactor, this should move to ProfileManager or Config
CURRENT_RESUME_INFO = """
Software Engineer with 5 years of experience in Python, AWS, and Web Development.
Education: BS in Computer Science.
Key Skills: Python, Django, React, Docker, Kubernetes.
"""


class DraftPreparationService:
    """
    Orchestrates the draft-first lifecycle for job applications.

    This service coordinates:
    1. Scraping job details
    2. Resume preparation
    3. Form prefilling (NO SUBMISSION)
    4. Draft persistence
    
    The result is always a saved draft, never a submitted application.
    """
    
    def __init__(
        self,
        job_manager: JobManagerProtocol,
        browser_agent: BrowserAgentProtocol,
        resume_builder: ResumeBuilderProtocol,
        draft_manager: Optional[DraftManager] = None
    ):
        """
        Initializes the service with required dependencies.

        Args:
            job_manager: Implementation of JobManagerProtocol for job status tracking.
            browser_agent: Implementation of BrowserAgentProtocol for web interaction.
            resume_builder: Implementation of ResumeBuilderProtocol for PDF generation.
            draft_manager: DraftManager instance (created if not provided).
        """
        self.job_manager = job_manager
        self.browser_agent = browser_agent
        self.resume_builder = resume_builder
        self.draft_manager = draft_manager or DraftManager()

    async def prepare_draft(
        self, 
        job_link: str, 
        user_details_text: str, 
        log_callback: Callable[[str], None] = print
    ) -> Optional[str]:
        """
        Prepares a job application draft without submitting.

        Workflow:
        1. Create initial draft entry
        2. Scrape job details from the provided link
        3. Generate/use resume PDF
        4. Prefill form fields (NO SUBMISSION)
        5. Extract and save FormState
        6. Update draft with final status

        Args:
            job_link: The URL of the job posting to process.
            user_details_text: Structured textual representation of the user's profile.
            log_callback: Optional function to handle progress logging.

        Returns:
            Draft ID if successful, None otherwise.
        """
        log_callback(f"📝 Preparing draft for: {job_link}")
        
        # Step 0: Create initial draft entry
        draft_id = self.draft_manager.create_draft(
            job_url=job_link,
            status=DraftStatus.JOB_FOUND
        )
        log_callback(f"Created draft: {draft_id}")
        
        # Also update legacy job manager for backwards compatibility
        self.job_manager.update_job(job_link, status="Running - Scraping")
        
        try:
            # Step 1: Scrape Job Details
            log_callback("🔍 Scraping job details...")
            job_description = await self.browser_agent.scrape_job_details(job_link)
            
            # Update draft with job details
            self.draft_manager.update_draft(
                draft_id,
                status=DraftStatus.EXTRACTED,
                job_details=job_description[:2000] if job_description else None
            )
            self.job_manager.update_job(job_link, details=job_description[:500] + "...") 
            log_callback("✅ Job details extracted")

            # Step 2: Resume Preparation
            from src.profile_manager import ProfileManager
            profile_manager = ProfileManager()
            profile = profile_manager.get_profile()
            
            use_uploaded = profile.get("use_uploaded_resume", False)
            uploaded_path = profile.get("uploaded_resume_path", "")
            
            pdf_path = None
            
            if use_uploaded and uploaded_path:
                if os.path.exists(uploaded_path):
                    log_callback(f"📄 Using uploaded resume: {uploaded_path}")
                    pdf_path = uploaded_path
                else:
                    log_callback(f"⚠️ Uploaded resume not found. Generating new one...")
                    pdf_path = self._generate_resume(job_link, job_description, log_callback)
            else:
                log_callback("📄 Generating tailored resume...")
                pdf_path = self._generate_resume(job_link, job_description, log_callback)
            
            self.draft_manager.update_draft(draft_id, resume_path=pdf_path)
            self.job_manager.update_job(job_link, pdf_path=pdf_path, status="Running - Prefilling")
            
            # Step 3: Prefill Form (NO SUBMISSION)
            log_callback("📝 Prefilling application form...")
            prefill_result = await self.browser_agent.prefill_form(
                job_link, 
                pdf_path, 
                user_details_text
            )
            
            # Step 4: Extract and save FormState
            form_state = self._extract_form_state(job_link, prefill_result)
            
            # Step 5: Save final draft
            self.draft_manager.update_draft(
                draft_id,
                status=DraftStatus.DRAFT_SAVED,
                form_state=form_state
            )
            
            # Update legacy job manager - clear any previous error message
            self.job_manager.update_job(job_link, status="Draft Saved", error_message="")
            
            validation_passed = prefill_result.get("validation_passed", False)
            field_count = len(form_state.fields)
            
            if validation_passed:
                log_callback(f"✅ Draft saved with {field_count} fields. Ready for manual review.")
            else:
                log_callback(f"⚠️ Draft saved with {field_count} fields. Some fields may need attention.")
            
            return draft_id

        except Exception as e:
            log_callback(f"❌ Error preparing draft: {e}")
            self.draft_manager.update_status(draft_id, DraftStatus.EXTRACTED)  # Partial state
            self.job_manager.update_job(job_link, status="Draft Failed", error_message=str(e))
            return None
    
    def _generate_resume(
        self, 
        job_link: str, 
        job_description: str, 
        log_callback: Callable[[str], None]
    ) -> str:
        """Generate a tailored resume PDF."""
        self.job_manager.update_job(job_link, status="Running - Generating Resume")
        job_id = abs(hash(job_link))
        pdf_path = self.resume_builder.build(job_description, CURRENT_RESUME_INFO, job_id=job_id)
        log_callback(f"✅ Resume generated: {pdf_path}")
        return pdf_path
    
    def _extract_form_state(self, job_link: str, prefill_result: dict) -> FormState:
        """Convert agent prefill result to FormState model."""
        fields = []
        
        for field_data in prefill_result.get("fields", []):
            field_type_str = field_data.get("field_type", "text").lower()
            try:
                field_type = FieldType(field_type_str)
            except ValueError:
                field_type = FieldType.TEXT
            
            fields.append(FieldState(
                field_id=field_data.get("field_id", "unknown"),
                field_type=field_type,
                label=field_data.get("label"),
                value=field_data.get("value"),
                confidence=field_data.get("confidence", 0.5),
                required=field_data.get("required", False)
            ))
        
        return FormState(
            job_url=job_link,
            fields=fields,
            extracted_at=datetime.utcnow(),
            last_modified=datetime.utcnow()
        )

    async def open_draft_in_browser(
        self,
        draft_id: str,
        log_callback: Callable[[str], None] = print
    ) -> bool:
        """
        Opens a saved draft in the browser for manual completion.
        
        This action:
        1. Retrieves the saved FormState
        2. Opens the job URL in browser
        3. Rehydrates all saved field values
        4. STOPS automation - user takes control
        
        Args:
            draft_id: The UUID of the draft to open.
            log_callback: Optional function for progress logging.
            
        Returns:
            True if the draft was successfully opened, False otherwise.
        """
        draft = self.draft_manager.get_draft(draft_id)
        
        if not draft:
            log_callback(f"❌ Draft not found: {draft_id}")
            return False
        
        if not draft.can_open():
            log_callback(f"⚠️ Draft cannot be opened (status: {draft.status})")
            return False
        
        log_callback(f"🌐 Opening draft in browser: {draft.job_url}")
        
        # Convert FormState to dict for agent
        form_state_dict = draft.form_state.model_dump() if draft.form_state else {}
        
        result = await self.browser_agent.open_draft(draft.job_url, form_state_dict)
        
        # Update draft status
        self.draft_manager.update_status(draft_id, DraftStatus.USER_OPENED)
        
        fields_restored = result.get("fields_restored", 0)
        fields_failed = result.get("fields_failed", 0)
        
        log_callback(f"✅ Draft opened. Restored {fields_restored} fields. User has control.")
        
        if fields_failed > 0:
            log_callback(f"⚠️ {fields_failed} fields could not be restored. Check notes.")
        
        return True


# Legacy alias for backwards compatibility
class JobApplicationService(DraftPreparationService):
    """
    DEPRECATED: Use DraftPreparationService instead.
    
    This class maintains backwards compatibility with existing code
    that references JobApplicationService.
    """
    
    async def process_job(
        self, 
        job_link: str, 
        user_details_text: str, 
        log_callback: Callable[[str], None] = print
    ) -> bool:
        """
        DEPRECATED: Use prepare_draft instead.
        
        This method now calls prepare_draft and returns a boolean
        for backwards compatibility.
        """
        draft_id = await self.prepare_draft(job_link, user_details_text, log_callback)
        return draft_id is not None
