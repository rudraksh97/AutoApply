"""
Core service layer for the AutoApply application.

This module contains the business logic for orchestrating the draft-first
workflow, coordinating between storage, browser automation, and resume generation.

WORKFLOW:
1. Browser agent extracts form structure (labels, xpaths) - NO FILLING
2. LLM generates answers based on user profile and job description
3. Draft is saved with values for extension to fill

CRITICAL: This service NEVER submits applications. All operations result in
saved drafts that users can open and complete manually.
"""

import json
import logging
from typing import Callable, Optional, List
from datetime import datetime
from urllib.parse import urljoin, urlparse
from src.interfaces import JobManagerProtocol, BrowserAgentProtocol, ResumeBuilderProtocol
from src.draft_manager import DraftManager
from api.schemas.form_state import FormState, FieldState, FieldType, DraftStatus, ResumeVersion
from src.prompts import GENERATE_FORM_ANSWERS_PROMPT
import uuid
import os

def get_user_profile_text() -> str:
    """
    Converts the user's profile into a structured text format for form filling.
    This replaces the hardcoded CURRENT_RESUME_INFO with actual profile data.
    """
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    
    basics = profile.get("basics", {})
    urls = profile.get("urls", {})
    demographics = profile.get("demographics", {})
    work_auth = profile.get("work_auth", {})
    education = profile.get("education", [])
    experience = profile.get("experience", [])
    
    # Build structured text
    lines = []
    
    # Personal Info
    lines.append("=== APPLICANT INFORMATION ===")
    lines.append(f"Full Name: {basics.get('first_name', '')} {basics.get('last_name', '')}")
    lines.append(f"Email: {basics.get('email', '')}")
    lines.append(f"Phone: {basics.get('phone', '')}")
    lines.append(f"Location: {basics.get('location', '')}")
    
    # URLs
    if urls:
        lines.append("")
        lines.append("=== LINKS ===")
        if urls.get("linkedin"):
            lines.append(f"LinkedIn: {urls.get('linkedin')}")
        if urls.get("github"):
            lines.append(f"GitHub: {urls.get('github')}")
        if urls.get("portfolio"):
            lines.append(f"Portfolio: {urls.get('portfolio')}")
    
    # Demographics
    if demographics:
        lines.append("")
        lines.append("=== DEMOGRAPHICS ===")
        lines.append(f"Gender: {demographics.get('gender', '')}")
        lines.append(f"Race/Ethnicity: {demographics.get('race', '')}")
        lines.append(f"Veteran Status: {demographics.get('veteran', '')}")
        lines.append(f"Disability Status: {demographics.get('disability', '')}")
    
    # Work Authorization
    if work_auth:
        lines.append("")
        lines.append("=== WORK AUTHORIZATION ===")
        lines.append(f"Authorized to work in US: {'Yes' if work_auth.get('authorized_in_us') else 'No'}")
        lines.append(f"Requires sponsorship: {'Yes' if work_auth.get('requires_sponsorship') else 'No'}")
    
    # Education
    if education:
        lines.append("")
        lines.append("=== EDUCATION ===")
        for edu in education:
            lines.append(f"- {edu.get('degree', '')} in {edu.get('field_of_study', '')} from {edu.get('university', '')} ({edu.get('graduation_year', '')})")
    
    # Experience
    if experience:
        lines.append("")
        lines.append("=== EXPERIENCE ===")
        for exp in experience:
            lines.append(f"- {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('start_date', '')} - {exp.get('end_date', '')})")
            if exp.get('description'):
                lines.append(f"  {exp.get('description')}")
    
    # Additional fields
    if profile.get("great_fit_pitch"):
        lines.append("")
        lines.append("=== WHY I'M A GREAT FIT ===")
        lines.append(profile.get("great_fit_pitch"))
    
    if profile.get("challenging_project"):
        lines.append("")
        lines.append("=== CHALLENGING PROJECT ===")
        lines.append(profile.get("challenging_project"))
    
    return "\n".join(lines)


# Legacy constant for backwards compatibility - now calls the function
CURRENT_RESUME_INFO = None  # Will be replaced at runtime


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
            # Step 1: Scrape Job Details AND Apply Link
            log_callback("🔍 Scraping job details and apply link...")
            scrape_result = await self.browser_agent.scrape_job_details(job_link)
            
            job_description = scrape_result.get("job_description", "")
            apply_link = scrape_result.get("apply_link")
            extracted_company = scrape_result.get("company_name")
            extracted_title = scrape_result.get("job_title")
            
            # Convert relative apply_link to absolute URL, default to job_link if not present
            if apply_link:
                if not urlparse(apply_link).scheme:
                    apply_link = urljoin(job_link, apply_link)
            else:
                apply_link = job_link
            
            # Update draft with job details
            self.draft_manager.update_draft(
                draft_id,
                status=DraftStatus.EXTRACTED,
                job_details=job_description[:2000] if job_description else None,
                apply_link=apply_link
            )
            # Store apply_link in job manager for reference
            self.job_manager.update_job(
                job_link, 
                details=job_description[:500] + "..." if job_description else None,
                apply_link=apply_link
            ) 
            
            if apply_link:
                log_callback(f"✅ Job details extracted. Apply link found: {apply_link}")
            else:
                log_callback("✅ Job details extracted (no separate apply link found)")

            # Step 2: Resume Preparation
            from src.profile_manager import ProfileManager
            profile_manager = ProfileManager()
            profile = profile_manager.get_profile()
            
            mode = profile.get("resume_generation_mode", "ats_generated")
            uploaded_pdf_path = profile.get("uploaded_pdf_path", "")
            uploaded_tex_path = profile.get("uploaded_tex_path", "")
            
            pdf_path = None
            relative_resume_path: Optional[str] = None
            
            if mode == "uploaded_pdf" and uploaded_pdf_path:
                if os.path.exists(uploaded_pdf_path):
                    log_callback(f"📄 Using uploaded resume: {uploaded_pdf_path}")
                    pdf_path = uploaded_pdf_path
                else:
                    log_callback(f"⚠️ Mode set to 'Uploaded PDF' but file not found at {uploaded_pdf_path}. Falling back to ATS generation.")
                    pdf_path = await self._generate_resume(draft_id, job_link, job_description, log_callback)
            
            else:
                # Default "ats_generated"
                log_callback("📄 Generating tailored resume using ATS workflow...")
                # If they have a custom template uploaded, use it
                template_path = uploaded_tex_path if uploaded_tex_path and os.path.exists(uploaded_tex_path) else None
                if template_path:
                    log_callback(f"  - Using custom template: {template_path}")
                
                pdf_path = await self._generate_resume(draft_id, job_link, job_description, log_callback, template_path=template_path)
            
            # Derive a project-relative path for API/static serving and a host-visible path
            # for legacy flows that need direct filesystem access.
            if pdf_path:
                host_root = os.getenv("HOST_PROJECT_ROOT")

                # Compute a project-relative path (e.g. "data/generated_resumes/Resume_123.pdf")
                rel_path_for_static = pdf_path
                if os.path.isabs(pdf_path):
                    # Container images typically mount the project at /app
                    rel_path_for_static = os.path.relpath(pdf_path, "/app")

                # Normalise to forward slashes for URLs/JSON
                rel_path_for_static = rel_path_for_static.replace("\\", "/")
                relative_resume_path = rel_path_for_static

                # Preserve existing behaviour for host-visible absolute paths
                if host_root:
                    pdf_host_path = os.path.join(host_root, rel_path_for_static).replace("\\", "/")
                    pdf_path = pdf_host_path
                else:
                    # Fallback to project-relative with forward slashes
                    pdf_path = rel_path_for_static
            
            # Step 2.1: Inject resume path into form fields if they are of type FILE
            # This ensures the extension knows WHERE the file is on the host
            # We do this AFTER Step 5 (LLM generation) but we need to track it.
            # Actually, let's do it after the form structure is extraction and LLM answers are generated.
            # For now, store it in the draft's resume_path.
            
            self.draft_manager.update_draft(
                draft_id, 
                resume_path=pdf_path
            )
            self.job_manager.update_job(job_link, pdf_path=pdf_path, status="Running - Extracting Form")
            
            # Step 3: Extract Form Structure (NO FILLING)
            log_callback("🔍 Extracting form structure...")
            
            # Determine which URL to use for form extraction
            # Priority: 1) Extracted apply_link, 2) Ashby special handling, 3) Original job_link
            extract_link = job_link
            
            if apply_link:
                # Use the apply link extracted by the agent
                extract_link = apply_link
                log_callback(f"📋 Using extracted apply link: {extract_link}")
            elif "jobs.ashbyhq.com" in job_link and "/application" not in job_link:
                # Fallback: Ashby special handling
                extract_link = job_link.rstrip("/") + "/application"
                log_callback(f"ℹ️ Ashby link detected. Extracting from: {extract_link}")
            else:
                log_callback(f"📋 Extracting form from: {extract_link}")

            extraction_result = await self.browser_agent.extract_form(extract_link)
            
            # Step 4: Convert to FormState (structure only, no values)
            form_state = self._extract_form_structure(job_link, extraction_result)
            field_count = len(form_state.fields)
            log_callback(f"📋 Found {field_count} form fields")
            
            # Step 5: Generate answers using LLM
            self.job_manager.update_job(job_link, status="Running - Generating Answers")
            form_state = await self._generate_form_answers(
                form_state,
                job_description,
                user_details_text,
                log_callback
            )
            
            # Step 5.1: Automatically inject resume path into fields of type FILE
            # if they look like a resume/CV field.
            if pdf_path:
                for field in form_state.fields:
                    if field.field_type == FieldType.FILE:
                        label = (field.label or "").lower()
                        if not label or any(kw in label for kw in ["resume", "cv", "document", "upload"]):
                            log_callback(f"🔗 Injecting resume path into field: {field.label or field.xpath}")
                            field.value = pdf_path
                            field.skipped = False # Force fill
            
            # Step 5.2: Expose project-relative resume path for the browser extension.
            # This lets the extension download the resume via the API and synthesize
            # a File object without needing direct filesystem access.
            if relative_resume_path:
                form_state.relative_resume_path = relative_resume_path
            
            # Step 6: Save final draft
            self.draft_manager.update_draft(
                draft_id,
                status=DraftStatus.DRAFT_SAVED,
                form_state=form_state
            )
            
            # Update legacy job manager - clear any previous error message
            self.job_manager.update_job(job_link, status="Draft Saved", error_message="")
            
            filled_count = sum(1 for f in form_state.fields if f.value and not f.skipped)
            skipped_count = sum(1 for f in form_state.fields if f.skipped)
            
            if skipped_count == 0:
                log_callback(f"✅ Draft saved with {filled_count}/{field_count} fields filled. Ready for review.")
            else:
                log_callback(f"⚠️ Draft saved: {filled_count} filled, {skipped_count} need your input.")
            
            return draft_id

        except Exception as e:
            log_callback(f"❌ Error preparing draft: {e}")
            self.draft_manager.update_status(draft_id, DraftStatus.FAILED)
            self.job_manager.update_job(job_link, status="Draft Failed", error_message=str(e))
            return None
    
    async def _generate_resume(
        self, 
        draft_id: str,
        job_link: str, 
        job_description: str, 
        log_callback: Callable[[str], None],
        template_path: Optional[str] = None
    ) -> str:
        """Generate a tailored resume PDF and track its version."""
        self.job_manager.update_job(job_link, status="Running - Generating Resume")
        
        # Use a stable hash for the job_id to ensure consistent filesystem paths across restarts
        from src.url_utils import get_stable_job_id
        job_id = get_stable_job_id(job_link)
        
        # 1. Fetch tailoring prompt from config
        from src.config import ConfigManager
        config_manager = ConfigManager()
        prompts = config_manager.get_ats_prompts()
        tailoring_prompt = prompts.get("tailor_resume")
        
        # 2. Calculate INITIAL ATS Score if not already done
        # We use a base rendering or just user profile text vs JD
        # To be precise, let's score the profile text against the JD
        log_callback("📊 Calculating initial ATS score...")
        initial_score_data = await self.resume_builder.calculate_ats_score(job_description, get_user_profile_text())
        initial_score = initial_score_data.get("score", 0)
        
        self.draft_manager.update_draft(draft_id, initial_ats_score=initial_score)
        log_callback(f"  - Initial Score: {initial_score}/100")

        # 3. Create initial ResumeVersion entry (before async build to avoid race condition)
        import uuid
        version_id = str(uuid.uuid4())
        
        v1 = ResumeVersion(
            id=version_id,
            draft_id=draft_id,
            version_number=1,
            tex_path=f"data/tex_resumes/{job_id}/v1/Resume_{job_id}_v1.tex", # Predicted path
            pdf_path=f"data/generated_resumes/{job_id}/v1/Resume_{job_id}_v1.pdf", # Predicted path
            ats_score=0, # Will be updated by background process
            justification="Generating...",
            keywords_added="",
            changes_summary="Initial tailored version",
            status="GENERATING",
            is_current=True
        )
        self.draft_manager.create_resume_version(v1)

        # 4. Synchronously Build version v1
        # The builder will update the DB entry with actual score, keywords, and status="COMPLETED"
        pdf_path, tex_path, keywords, changes = await self.resume_builder.build(
            job_description, 
            get_user_profile_text(), 
            job_id=job_id,
            template_path=template_path,
            tailoring_prompt=tailoring_prompt,
            version="v1",
            version_id=version_id,
            draft_id=draft_id,
            draft_manager=self.draft_manager,
            ats_context=initial_score_data,
            job_manager=self.job_manager,
            job_url=job_link
        )
        
        log_callback(f"✅ Resume generation completed for v1")
        return pdf_path
    
    def _extract_form_structure(self, job_link: str, extraction_result: dict) -> FormState:
        """
        Convert browser agent extraction result to FormState model.
        This only contains structure (xpath, label, options) - no values yet.
        """
        fields = []
        
        # Map common field_type variations to FieldType enum values
        field_type_mapping = {
            "text": FieldType.TEXT,
            "email": FieldType.EMAIL,
            "phone": FieldType.PHONE,
            "tel": FieldType.PHONE,
            "select": FieldType.SELECT,
            "dropdown": FieldType.SELECT,
            "checkbox": FieldType.CHECKBOX,
            "radio": FieldType.RADIO,
            "file": FieldType.FILE,
            "textarea": FieldType.TEXTAREA,
            "hidden": FieldType.HIDDEN,
            "password": FieldType.TEXT,
        }
        
        for field_data in extraction_result.get("fields", []):
            field_type_str = field_data.get("field_type", "text").lower()
            field_type = field_type_mapping.get(field_type_str, FieldType.TEXT)
            
            # Get xpath - fallback to field_id for backwards compatibility
            xpath = field_data.get("xpath") or field_data.get("field_id", "//unknown")
            
            fields.append(FieldState(
                xpath=xpath,
                field_type=field_type,
                label=field_data.get("label"),
                options=field_data.get("options"),  # For select/radio fields
                value=None,  # No value yet - will be filled by LLM
                confidence=0.0,
                required=field_data.get("required", False),
                skipped=False,
                skip_reason=None
            ))
        
        return FormState(
            job_url=job_link,
            fields=fields,
            extracted_at=datetime.utcnow(),
            last_modified=datetime.utcnow()
        )
    
    async def _generate_form_answers(
        self,
        form_state: FormState,
        job_description: str,
        user_profile_text: str,
        log_callback: Callable[[str], None] = print
    ) -> FormState:
        """
        Use LLM to generate answers for each form field based on user profile.
        Updates the FormState with values and confidence scores.
        """
        from langchain_openai import ChatOpenAI
        
        # Prepare fields for LLM (convert to simple dict format)
        fields_for_llm = []
        for field in form_state.fields:
            fields_for_llm.append({
                "xpath": field.xpath,
                "field_type": field.field_type.value,
                "label": field.label,
                "required": field.required,
                "options": field.options
            })
        
        # Build prompt
        prompt = GENERATE_FORM_ANSWERS_PROMPT.format(
            job_description=job_description[:2000] if job_description else "No description available",
            user_profile=user_profile_text,
            form_fields=json.dumps(fields_for_llm, indent=2)
        )
        
        try:
            # Use OpenRouter for LLM
            import os
            llm = ChatOpenAI(
                model="google/gemini-2.0-flash-001",
                openai_api_key=os.getenv("OPENROUTER_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.3
            )
            
            log_callback("🤖 Generating form answers with LLM...")
            response = await llm.ainvoke(prompt)
            response_text = response.content
            
            # Parse LLM response
            try:
                # Try to extract JSON array from response
                import re
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    answers = json.loads(json_match.group())
                else:
                    answers = json.loads(response_text)
            except json.JSONDecodeError:
                log_callback("⚠️ Failed to parse LLM response as JSON")
                return form_state
            
            # Map answers back to form state
            answer_map = {a.get("xpath"): a for a in answers}
            
            for field in form_state.fields:
                if field.xpath in answer_map:
                    answer = answer_map[field.xpath]
                    # Ensure value is always a string or None
                    raw_value = answer.get("value")
                    if raw_value is None:
                        field.value = None
                    elif isinstance(raw_value, bool):
                        field.value = str(raw_value).lower()
                    else:
                        field.value = str(raw_value)
                    field.confidence = answer.get("confidence", 0.5)
                    field.skipped = answer.get("skip", False)
                    field.skip_reason = answer.get("skip_reason")
            
            form_state.last_modified = datetime.utcnow()
            filled_count = sum(1 for f in form_state.fields if f.value and not f.skipped)
            log_callback(f"✅ Generated answers for {filled_count}/{len(form_state.fields)} fields")
            
            return form_state
            
        except Exception as e:
            log_callback(f"⚠️ LLM answer generation failed: {e}")
            return form_state
    
    # Legacy alias for backwards compatibility
    def _extract_form_state(self, job_link: str, prefill_result: dict) -> FormState:
        return self._extract_form_structure(job_link, prefill_result)

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
