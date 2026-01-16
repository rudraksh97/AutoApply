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
import os
import re
import uuid
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

from langchain_openai import ChatOpenAI

from api.schemas.form_state import (
    DraftStatus,
    FieldState,
    FieldType,
    FormState,
    ResumeVersion,
)
from src.draft_manager import DraftManager
from src.interfaces import (
    BrowserAgentProtocol,
    JobManagerProtocol,
    ResumeBuilderProtocol,
)
from src.prompts import GENERATE_FORM_ANSWERS_PROMPT


# =============================================================================
# Profile Text Generation
# =============================================================================

def get_user_profile_text() -> str:
    """Convert the user's profile into structured text for form filling."""
    from src.profile_manager import ProfileManager

    pm = ProfileManager()
    profile = pm.get_profile()

    return _format_profile_as_text(profile)


def _format_profile_as_text(profile: dict) -> str:
    """Format a profile dictionary as structured text."""
    lines = []

    # Personal Info
    basics = profile.get("basics", {})
    lines.append("=== APPLICANT INFORMATION ===")
    lines.append(f"Full Name: {basics.get('first_name', '')} {basics.get('last_name', '')}")
    lines.append(f"Email: {basics.get('email', '')}")
    lines.append(f"Phone: {basics.get('phone', '')}")
    lines.append(f"Location: {basics.get('location', '')}")

    # URLs
    urls = profile.get("urls", {})
    if urls:
        lines.append("")
        lines.append("=== LINKS ===")
        for key in ["linkedin", "github", "portfolio"]:
            if urls.get(key):
                lines.append(f"{key.title()}: {urls[key]}")

    # Demographics
    demographics = profile.get("demographics", {})
    if demographics:
        lines.append("")
        lines.append("=== DEMOGRAPHICS ===")
        lines.append(f"Gender: {demographics.get('gender', '')}")
        lines.append(f"Race/Ethnicity: {demographics.get('race', '')}")
        lines.append(f"Veteran Status: {demographics.get('veteran', '')}")
        lines.append(f"Disability Status: {demographics.get('disability', '')}")

    # Work Authorization
    work_auth = profile.get("work_auth", {})
    if work_auth:
        lines.append("")
        lines.append("=== WORK AUTHORIZATION ===")
        authorized = "Yes" if work_auth.get("authorized_in_us") else "No"
        sponsorship = "Yes" if work_auth.get("requires_sponsorship") else "No"
        lines.append(f"Authorized to work in US: {authorized}")
        lines.append(f"Requires sponsorship: {sponsorship}")

    # Education
    education = profile.get("education", [])
    if education:
        lines.append("")
        lines.append("=== EDUCATION ===")
        for edu in education:
            degree = edu.get("degree", "")
            field = edu.get("field_of_study", "")
            uni = edu.get("university", "")
            year = edu.get("graduation_year", "")
            lines.append(f"- {degree} in {field} from {uni} ({year})")

    # Experience
    experience = profile.get("experience", [])
    if experience:
        lines.append("")
        lines.append("=== EXPERIENCE ===")
        for exp in experience:
            role = exp.get("role", "")
            company = exp.get("company", "")
            start = exp.get("start_date", "")
            end = exp.get("end_date", "")
            lines.append(f"- {role} at {company} ({start} - {end})")
            if exp.get("description"):
                lines.append(f"  {exp['description']}")

    # Additional fields
    if profile.get("great_fit_pitch"):
        lines.append("")
        lines.append("=== WHY I'M A GREAT FIT ===")
        lines.append(profile["great_fit_pitch"])

    if profile.get("challenging_project"):
        lines.append("")
        lines.append("=== CHALLENGING PROJECT ===")
        lines.append(profile["challenging_project"])

    return "\n".join(lines)


# =============================================================================
# Field Type Mapping
# =============================================================================

FIELD_TYPE_MAP = {
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


# =============================================================================
# Draft Preparation Service
# =============================================================================

class DraftPreparationService:
    """
    Orchestrates the draft-first lifecycle for job applications.

    This service coordinates:
    1. Scraping job details
    2. Resume preparation
    3. Form extraction (NO SUBMISSION)
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
        self.job_manager = job_manager
        self.browser_agent = browser_agent
        self.resume_builder = resume_builder
        self.draft_manager = draft_manager or DraftManager()

    # -------------------------------------------------------------------------
    # Main Entry Point
    # -------------------------------------------------------------------------

    async def prepare_draft(
        self,
        job_link: str,
        user_details_text: str,
        log_callback: Callable[[str], None] = print
    ) -> Optional[str]:
        """
        Prepare a job application draft without submitting.

        Returns:
            Draft ID if successful, None otherwise.
        """
        log_callback(f"📝 Preparing draft for: {job_link}")

        draft_id = self._create_initial_draft(job_link)
        log_callback(f"Created draft: {draft_id}")

        try:
            # Step 1: Scrape job details
            job_data = await self._scrape_job(job_link, log_callback)

            # Step 2: Update draft with scraped data
            self._update_draft_with_job_data(draft_id, job_link, job_data, log_callback)

            # Step 3: Prepare resume
            pdf_path, relative_path = await self._prepare_resume(
                draft_id, job_link, job_data["description"], log_callback
            )

            # Step 4: Extract form structure
            extract_url = self._determine_extract_url(job_link, job_data["apply_link"], log_callback)
            form_state = await self._extract_and_fill_form(
                job_link, extract_url, job_data["description"],
                user_details_text, pdf_path, relative_path, log_callback
            )

            # Step 5: Save final draft
            self._save_final_draft(draft_id, job_link, form_state, log_callback)

            return draft_id

        except Exception as e:
            log_callback(f"❌ Error preparing draft: {e}")
            self.draft_manager.update_status(draft_id, DraftStatus.FAILED)
            self.job_manager.update_job(job_link, status="Draft Failed", error_message=str(e))
            return None

    # -------------------------------------------------------------------------
    # Step 1: Create Draft
    # -------------------------------------------------------------------------

    def _create_initial_draft(self, job_link: str) -> str:
        """Create initial draft entry and update job manager."""
        draft_id = self.draft_manager.create_draft(
            job_url=job_link,
            status=DraftStatus.JOB_FOUND
        )
        self.job_manager.update_job(job_link, status="Running - Scraping")
        return draft_id

    # -------------------------------------------------------------------------
    # Step 2: Scrape Job
    # -------------------------------------------------------------------------

    async def _scrape_job(self, job_link: str, log_callback: Callable) -> dict:
        """Scrape job details from the job posting."""
        log_callback("🔍 Scraping job details and apply link...")

        result = await self.browser_agent.scrape_job_details(job_link)

        apply_link = result.get("apply_link")
        if apply_link and not urlparse(apply_link).scheme:
            apply_link = urljoin(job_link, apply_link)

        return {
            "description": result.get("job_description", ""),
            "apply_link": apply_link or job_link,
            "company": result.get("company_name"),
            "title": result.get("job_title"),
        }

    def _update_draft_with_job_data(
        self, draft_id: str, job_link: str, job_data: dict, log_callback: Callable
    ):
        """Update draft and job manager with scraped job data."""
        description = job_data["description"]
        apply_link = job_data["apply_link"]

        self.draft_manager.update_draft(
            draft_id,
            status=DraftStatus.EXTRACTED,
            job_details=description[:2000] if description else None,
            apply_link=apply_link
        )

        self.job_manager.update_job(
            job_link,
            details=description[:500] + "..." if description else None,
            apply_link=apply_link
        )

        if apply_link:
            log_callback(f"✅ Job details extracted. Apply link: {apply_link}")
        else:
            log_callback("✅ Job details extracted (no separate apply link)")

    # -------------------------------------------------------------------------
    # Step 3: Resume Preparation
    # -------------------------------------------------------------------------

    async def _prepare_resume(
        self,
        draft_id: str,
        job_link: str,
        job_description: str,
        log_callback: Callable
    ) -> tuple[Optional[str], Optional[str]]:
        """Prepare resume - either use uploaded or generate new."""
        from src.profile_manager import ProfileManager

        profile_manager = ProfileManager()
        profile = profile_manager.get_profile()

        mode = profile.get("resume_generation_mode", "ats_generated")
        uploaded_pdf = profile_manager.get_current_resume_path("pdf")
        uploaded_tex = profile_manager.get_current_resume_path("text")

        # Determine PDF path based on mode
        if mode == "uploaded_pdf" and uploaded_pdf and os.path.exists(uploaded_pdf):
            log_callback(f"📄 Using uploaded resume: {uploaded_pdf}")
            pdf_path = uploaded_pdf
        else:
            if mode == "uploaded_pdf":
                log_callback("⚠️ Uploaded PDF not found. Falling back to ATS generation.")

            log_callback("📄 Generating tailored resume...")
            template = uploaded_tex if uploaded_tex and os.path.exists(uploaded_tex) else None
            if template:
                log_callback(f"  - Using template: {template}")

            pdf_path = await self._generate_resume(
                draft_id, job_link, job_description, log_callback, template
            )

        # Compute paths for storage
        pdf_path, relative_path = self._compute_resume_paths(pdf_path)

        # Update draft with resume path
        self.draft_manager.update_draft(draft_id, resume_path=pdf_path)
        self.job_manager.update_job(job_link, pdf_path=pdf_path, status="Running - Extracting Form")

        return pdf_path, relative_path

    def _compute_resume_paths(self, pdf_path: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """Compute absolute and relative paths for the resume."""
        if not pdf_path:
            return None, None

        host_root = os.getenv("HOST_PROJECT_ROOT")

        # Compute project-relative path
        rel_path = pdf_path
        if os.path.isabs(pdf_path):
            rel_path = os.path.relpath(pdf_path, "/app")
        rel_path = rel_path.replace("\\", "/")

        # Compute final path
        if host_root:
            final_path = os.path.join(host_root, rel_path).replace("\\", "/")
        else:
            final_path = rel_path

        return final_path, rel_path

    async def _generate_resume(
        self,
        draft_id: str,
        job_link: str,
        job_description: str,
        log_callback: Callable,
        template_path: Optional[str] = None
    ) -> str:
        """Generate a tailored resume PDF."""
        from src.config import ConfigManager
        from src.url_utils import get_stable_job_id

        self.job_manager.update_job(job_link, status="Running - Generating Resume")

        job_id = get_stable_job_id(job_link)
        config = ConfigManager()
        tailoring_prompt = config.get_ats_prompts().get("tailor_resume")

        # Calculate initial ATS score
        log_callback("📊 Calculating initial ATS score...")
        score_data = await self.resume_builder.calculate_ats_score(
            job_description, get_user_profile_text()
        )
        initial_score = score_data.get("score", 0)
        self.draft_manager.update_draft(draft_id, initial_ats_score=initial_score)
        log_callback(f"  - Initial Score: {initial_score}/100")

        # Create version entry
        version_id = str(uuid.uuid4())
        version = ResumeVersion(
            id=version_id,
            draft_id=draft_id,
            version_number=1,
            tex_path=f"data/tex_resumes/{job_id}/v1/Resume_{job_id}_v1.tex",
            pdf_path=f"data/generated_resumes/{job_id}/v1/Resume_{job_id}_v1.pdf",
            ats_score=0,
            justification="Generating...",
            keywords_added="",
            changes_summary="Initial tailored version",
            status="GENERATING",
            is_current=True
        )
        self.draft_manager.create_resume_version(version)

        # Build resume
        pdf_path, _, _, _ = await self.resume_builder.build(
            job_description,
            get_user_profile_text(),
            job_id=job_id,
            template_path=template_path,
            tailoring_prompt=tailoring_prompt,
            version="v1",
            version_id=version_id,
            draft_id=draft_id,
            draft_manager=self.draft_manager,
            ats_context=score_data,
            job_manager=self.job_manager,
            job_url=job_link
        )

        log_callback("✅ Resume generation completed")
        return pdf_path

    # -------------------------------------------------------------------------
    # Step 4: Form Extraction
    # -------------------------------------------------------------------------

    def _determine_extract_url(
        self, job_link: str, apply_link: Optional[str], log_callback: Callable
    ) -> str:
        """Determine which URL to use for form extraction."""
        if apply_link and apply_link != job_link:
            log_callback(f"📋 Using apply link: {apply_link}")
            return apply_link

        # ATS-specific URL patterns
        if "jobs.ashbyhq.com" in job_link and "/application" not in job_link:
            url = job_link.rstrip("/") + "/application"
            log_callback(f"ℹ️ Ashby detected. Using: {url}")
            return url

        if "apply.workable.com" in job_link and "/apply" not in job_link:
            url = job_link.rstrip("/") + "/apply"
            log_callback(f"ℹ️ Workable detected. Using: {url}")
            return url

        log_callback(f"📋 Extracting form from: {job_link}")
        return job_link

    async def _extract_and_fill_form(
        self,
        job_link: str,
        extract_url: str,
        job_description: str,
        user_details_text: str,
        pdf_path: Optional[str],
        relative_path: Optional[str],
        log_callback: Callable
    ) -> FormState:
        """Extract form structure and generate answers."""
        log_callback("🔍 Extracting form structure...")

        extraction = await self.browser_agent.extract_form(extract_url)
        form_state = self._parse_form_extraction(job_link, extraction)

        field_count = len(form_state.fields)
        if field_count == 0:
            if extraction.get("status") == "no_form_found":
                log_callback("⚠️ No form fields found on this page.")
            else:
                raise ValueError("Form extraction found 0 fields.")

        log_callback(f"📋 Found {field_count} form fields")

        # Generate answers
        self.job_manager.update_job(job_link, status="Running - Generating Answers")
        form_state = await self._generate_form_answers(
            form_state, job_description, user_details_text, log_callback
        )

        # Inject resume path into file fields
        self._inject_resume_into_form(form_state, pdf_path, log_callback)

        if relative_path:
            form_state.relative_resume_path = relative_path

        return form_state

    def _parse_form_extraction(self, job_link: str, extraction: dict) -> FormState:
        """Convert extraction result to FormState model."""
        fields = []

        for field_data in extraction.get("fields", []):
            field_type_str = field_data.get("field_type", "text").lower()
            field_type = FIELD_TYPE_MAP.get(field_type_str, FieldType.TEXT)
            xpath = field_data.get("xpath") or field_data.get("field_id", "//unknown")

            fields.append(FieldState(
                xpath=xpath,
                field_type=field_type,
                label=field_data.get("label"),
                options=field_data.get("options"),
                value=None,
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

    def _inject_resume_into_form(
        self, form_state: FormState, pdf_path: Optional[str], log_callback: Callable
    ):
        """Inject resume path into FILE type fields."""
        if not pdf_path:
            return

        resume_keywords = ["resume", "cv", "document", "upload"]

        for field in form_state.fields:
            if field.field_type == FieldType.FILE:
                label = (field.label or "").lower()
                if not label or any(kw in label for kw in resume_keywords):
                    log_callback(f"🔗 Injecting resume into: {field.label or field.xpath}")
                    field.value = pdf_path
                    field.skipped = False

    async def _generate_form_answers(
        self,
        form_state: FormState,
        job_description: str,
        user_profile_text: str,
        log_callback: Callable
    ) -> FormState:
        """Generate answers for form fields using LLM."""
        fields_for_llm = [
            {
                "xpath": f.xpath,
                "field_type": f.field_type.value,
                "label": f.label,
                "required": f.required,
                "options": f.options
            }
            for f in form_state.fields
        ]

        prompt = GENERATE_FORM_ANSWERS_PROMPT.format(
            job_description=job_description[:2000] if job_description else "No description",
            user_profile=user_profile_text,
            form_fields=json.dumps(fields_for_llm, indent=2)
        )

        try:
            llm = ChatOpenAI(
                model="google/gemini-2.0-flash-001",
                openai_api_key=os.getenv("OPENROUTER_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.3
            )

            log_callback("🤖 Generating form answers...")
            response = await llm.ainvoke(prompt)
            answers = self._parse_llm_answers(response.content)

            self._apply_answers_to_form(form_state, answers)

            filled = sum(1 for f in form_state.fields if f.value and not f.skipped)
            log_callback(f"✅ Generated answers for {filled}/{len(form_state.fields)} fields")

        except Exception as e:
            log_callback(f"⚠️ LLM answer generation failed: {e}")

        return form_state

    def _parse_llm_answers(self, response_text: str) -> list:
        """Parse LLM response to extract answers."""
        try:
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response_text)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse answers: {response_text[:200]}...")

    def _apply_answers_to_form(self, form_state: FormState, answers: list):
        """Apply parsed answers to form state."""
        answer_map = {a.get("xpath"): a for a in answers}

        for field in form_state.fields:
            if field.xpath not in answer_map:
                continue

            answer = answer_map[field.xpath]
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

    # -------------------------------------------------------------------------
    # Step 5: Save Draft
    # -------------------------------------------------------------------------

    def _save_final_draft(
        self, draft_id: str, job_link: str, form_state: FormState, log_callback: Callable
    ):
        """Save the final draft with form state."""
        self.draft_manager.update_draft(
            draft_id,
            status=DraftStatus.DRAFT_SAVED,
            form_state=form_state
        )
        self.job_manager.update_job(job_link, status="Draft Saved", error_message="")

        filled = sum(1 for f in form_state.fields if f.value and not f.skipped)
        skipped = sum(1 for f in form_state.fields if f.skipped)
        total = len(form_state.fields)

        if skipped == 0:
            log_callback(f"✅ Draft saved: {filled}/{total} fields filled. Ready for review.")
        else:
            log_callback(f"⚠️ Draft saved: {filled} filled, {skipped} need your input.")

    # -------------------------------------------------------------------------
    # Open Draft in Browser
    # -------------------------------------------------------------------------

    async def open_draft_in_browser(
        self,
        draft_id: str,
        log_callback: Callable[[str], None] = print
    ) -> bool:
        """
        Open a saved draft in the browser for manual completion.

        After opening, browser automation ENDS and user takes control.
        """
        draft = self.draft_manager.get_draft(draft_id)

        if not draft:
            log_callback(f"❌ Draft not found: {draft_id}")
            return False

        if not draft.can_open():
            log_callback(f"⚠️ Draft cannot be opened (status: {draft.status})")
            return False

        log_callback(f"🌐 Opening draft: {draft.job_url}")

        form_state_dict = draft.form_state.model_dump() if draft.form_state else {}
        result = await self.browser_agent.open_draft(draft.job_url, form_state_dict)

        self.draft_manager.update_status(draft_id, DraftStatus.USER_OPENED)

        restored = result.get("fields_restored", 0)
        failed = result.get("fields_failed", 0)

        log_callback(f"✅ Restored {restored} fields. User has control.")
        if failed > 0:
            log_callback(f"⚠️ {failed} fields could not be restored.")

        return True
