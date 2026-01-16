"""
API router for draft management endpoints.

This router provides endpoints for managing application drafts in the
draft-first workflow. Users can list, view, and open drafts for manual completion.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel
import os
import json

from src.draft_manager import DraftManager
from api.schemas.form_state import ApplicationDraft, DraftSummary, DraftStatus, ResumeVersion
from src.services import get_user_profile_text

router = APIRouter(prefix="/drafts", tags=["Drafts"])

# Initialize draft manager
draft_manager = DraftManager()


class DraftOpenRequest(BaseModel):
    """Request body for opening a draft in browser."""
    headless: bool = False  # Default to visible browser for user interaction


class DraftOpenResponse(BaseModel):
    """Response for draft open operation."""
    status: str
    fields_restored: int
    fields_failed: int
    notes: Optional[str] = None


@router.get("", response_model=List[DraftSummary])
async def list_drafts(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all saved application drafts.
    
    Returns lightweight summaries without full FormState to reduce payload size.
    
    Args:
        status: Optional filter by draft status (e.g., 'draft_saved', 'user_opened')
        limit: Maximum number of drafts to return
        offset: Number of drafts to skip for pagination
    
    Returns:
        List of draft summaries
    """
    summaries = draft_manager.get_all_summaries()
    
    # Filter by status if provided
    if status:
        try:
            status_enum = DraftStatus(status)
            summaries = [s for s in summaries if s.status == status_enum]
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in DraftStatus]}"
            )
    
    # Apply pagination
    return summaries[offset:offset + limit]


@router.get("/{draft_id}", response_model=ApplicationDraft)
async def get_draft(draft_id: str):
    """
    Get full details of a specific draft including FormState.
    
    Args:
        draft_id: The UUID of the draft
        
    Returns:
        Complete ApplicationDraft with all fields
    """
    draft = draft_manager.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    
    return draft


@router.delete("/{draft_id}")
async def delete_draft(draft_id: str):
    """
    Delete a draft.
    
    Args:
        draft_id: The UUID of the draft to delete
        
    Returns:
        Status message
    """
    success = draft_manager.delete_draft(draft_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    
    return {"status": "deleted", "draft_id": draft_id}


@router.post("/{draft_id}/open", response_model=DraftOpenResponse)
async def open_draft_in_browser(draft_id: str, request: DraftOpenRequest = None):
    """
    Open a saved draft in the browser for manual completion.
    
    This action:
    1. Retrieves the saved FormState
    2. Opens the job URL in a browser
    3. Rehydrates all saved field values
    4. Leaves the browser open for user control
    5. Updates draft status to 'user_opened'
    
    IMPORTANT: Browser automation ENDS after rehydration. The user takes
    manual control to review and submit the application.
    
    Args:
        draft_id: The UUID of the draft to open
        request: Optional configuration (e.g., headless mode)
        
    Returns:
        Status of the rehydration attempt
    """
    from src.agent import BrowserAgent
    from src.services import DraftPreparationService
    from src.job_manager import JobManager
    from src.resume_builder import ResumeBuilder
    
    draft = draft_manager.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    
    if not draft.can_open():
        raise HTTPException(
            status_code=400, 
            detail=f"Draft cannot be opened. Current status: {draft.status.value}. "
                   f"Draft must be in 'prefilled', 'draft_saved', or 'user_opened' state."
        )
    
    # Initialize browser agent with visible browser (not headless)
    headless = request.headless if request else False
    browser_agent = BrowserAgent(headless=headless)
    
    # Create service instance
    service = DraftPreparationService(
        job_manager=JobManager(),
        browser_agent=browser_agent,
        resume_builder=ResumeBuilder(),
        draft_manager=draft_manager
    )
    
    # Open the draft
    logs = []
    success = await service.open_draft_in_browser(
        draft_id=draft_id,
        log_callback=lambda msg: logs.append(msg)
    )
    
    if not success:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to open draft. Logs: {'; '.join(logs)}"
        )
    
    # Get updated draft to report field counts
    updated_draft = draft_manager.get_draft(draft_id)
    field_count = len(updated_draft.form_state.fields) if updated_draft and updated_draft.form_state else 0
    
    return DraftOpenResponse(
        status="opened",
        fields_restored=field_count,
        fields_failed=0,
        notes="; ".join(logs) if logs else "Draft opened successfully. Browser is now under user control."
    )


@router.get("/by-url/{job_url:path}", response_model=ApplicationDraft)
async def get_draft_by_url(job_url: str):
    """
    Get a draft by job URL.
    
    Args:
        job_url: The URL of the job posting
        
    Returns:
        The ApplicationDraft if found
    """
    draft = draft_manager.get_draft_by_url(job_url)
    
    if not draft:
        raise HTTPException(status_code=404, detail=f"No draft found for URL: {job_url}")
    
    return draft


class RemoteFillRequest(BaseModel):
    """Request body for remote browser fill."""
    chrome_host: str = "host.docker.internal"  # For Docker to host connection
    chrome_port: int = 9222


class RemoteFillResponse(BaseModel):
    """Response for remote browser fill."""
    success: bool
    fields_filled: int
    fields_failed: int
    message: str
    errors: List[str] = []


@router.post("/{draft_id}/fill-remote", response_model=RemoteFillResponse)
async def fill_draft_remote(draft_id: str, request: RemoteFillRequest = None):
    """
    Fill a draft form using the user's LOCAL Chrome browser via CDP.
    
    This requires Chrome to be running with remote debugging:
    
        Mac: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222
        Windows: chrome.exe --remote-debugging-port=9222
        Linux: google-chrome --remote-debugging-port=9222
    
    The Docker container connects to your Chrome and fills the form directly,
    so you can see it happening in your own browser!
    
    Args:
        draft_id: The UUID of the draft to fill
        request: Optional Chrome connection settings
        
    Returns:
        Status of the fill operation
    """
    from src.remote_browser import RemoteBrowserController
    import asyncio
    
    draft = draft_manager.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    
    if not draft.form_state:
        raise HTTPException(status_code=400, detail="Draft has no form state to fill")
    
    # Get connection settings
    host = request.chrome_host if request else "host.docker.internal"
    port = request.chrome_port if request else 9222
    
    controller = RemoteBrowserController(host=host, port=port)
    
    # Check if Chrome is available
    if not await controller.is_chrome_available():
        raise HTTPException(
            status_code=503,
            detail="Chrome not available. Please start Chrome with remote debugging:\n\n"
                   "Mac: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222\n\n"
                   "Windows: chrome.exe --remote-debugging-port=9222\n\n"
                   "Linux: google-chrome --remote-debugging-port=9222"
        )
    
    try:
        # Create new tab and navigate
        target = await controller.create_new_tab()
        await asyncio.sleep(0.5)
        
        await controller.navigate(target, draft.job_url)
        await asyncio.sleep(3)  # Wait for page to load
        
        # Fill the form
        form_state_dict = draft.form_state.model_dump()
        results = await controller.fill_form_from_state(target, form_state_dict)
        
        # Update draft status
        draft_manager.update_status(draft_id, DraftStatus.USER_OPENED)
        
        return RemoteFillResponse(
            success=True,
            fields_filled=results["filled"],
            fields_failed=results["failed"],
            message=f"Form opened in your Chrome! {results['filled']} fields filled.",
            errors=results["errors"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fill form: {str(e)}")


@router.get("/{draft_id}/fill-script")
async def get_fill_script(draft_id: str):
    """
    Get a JavaScript snippet to fill the form manually.
    
    This returns a script that can be pasted into the browser console
    to auto-fill the form fields from the saved draft.
    
    Usage:
    1. Open the job application URL
    2. Open browser console (F12 -> Console)
    3. Paste the script and press Enter
    
    Args:
        draft_id: The UUID of the draft
        
    Returns:
        JavaScript code to fill the form
    """
    draft = draft_manager.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    
    if not draft.form_state:
        raise HTTPException(status_code=400, detail="Draft has no form state")
    
    # Generate JavaScript fill script
    fields_js = []
    for field in draft.form_state.fields:
        if field.value and not field.skipped:
            escaped_value = field.value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            escaped_xpath = field.xpath.replace("\\", "\\\\").replace("'", "\\'")
            field_label = field.label or field.xpath
            fields_js.append(f"""
    // {field_label}
    fillFieldByXPath({json.dumps(field.xpath)}, {json.dumps(field.value)}, {json.dumps(field.field_type.value)});""")
    
    script = f"""
// AutoApply Form Filler - Draft: {draft_id}
// Paste this in your browser console (F12) on the job application page

(function() {{
    function getElementByXPath(xpath) {{
        try {{
            const result = document.evaluate(
                xpath,
                document,
                null,
                XPathResult.FIRST_ORDERED_NODE_TYPE,
                null
            );
            return result.singleNodeValue;
        }} catch (e) {{
            console.error('XPath error:', e);
            return null;
        }}
    }}
    
    function fillFieldByXPath(xpath, value, fieldType) {{
        const el = getElementByXPath(xpath);
        if (!el) {{
            console.log('❌ Not found by XPath: ' + xpath);
            return false;
        }}
        
        const elType = el.type || el.tagName.toLowerCase();
        
        try {{
            switch (elType) {{
                case 'checkbox':
                    const shouldCheck = ['true', '1', 'yes'].includes(String(value).toLowerCase());
                    if (el.checked !== shouldCheck) {{
                        el.checked = shouldCheck;
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    console.log('✅ Filled checkbox: ' + xpath);
                    return true;
                    
                case 'radio':
                    const radiogroup = document.querySelectorAll(`[name="${{el.name}}"]`);
                    let radioFound = false;
                    radiogroup.forEach(radio => {{
                        if (radio.value === value || 
                            radio.nextSibling?.textContent?.trim().toLowerCase().includes(String(value).toLowerCase())) {{
                            radio.checked = true;
                            radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            radioFound = true;
                        }}
                    }});
                    if (radioFound) {{
                        console.log('✅ Filled radio: ' + xpath);
                    }}
                    return radioFound;
                    
                case 'select':
                case 'select-one':
                case 'select-multiple':
                    const options = Array.from(el.options);
                    const match = options.find(opt => 
                        opt.value === value || 
                        opt.text.toLowerCase().includes(String(value).toLowerCase())
                    );
                    if (match) {{
                        el.value = match.value;
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        console.log('✅ Filled select: ' + xpath);
                        return true;
                    }}
                    console.log('❌ Option not found in select: ' + xpath);
                    return false;
                    
                case 'file':
                    console.log('⚠️ File input skipped: ' + xpath);
                    return false;
                    
                default:
                    el.focus();
                    el.value = value;
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    el.blur();
                    console.log('✅ Filled: ' + xpath);
                    return true;
            }}
        }} catch (e) {{
            console.error('Error filling field:', e);
            return false;
        }}
    }}
    
    console.log('🚀 AutoApply filling {len([f for f in draft.form_state.fields if f.value and not f.skipped])} fields...');
    {"".join(fields_js)}
    console.log('✅ Done! Review the form and submit when ready.');
}})();
"""
    
    return {
        "draft_id": draft_id,
        "job_url": draft.job_url,
        "field_count": len(draft.form_state.fields),
        "script": script,
        "instructions": [
            f"1. Open: {draft.job_url}",
            "2. Press F12 to open Developer Tools",
            "3. Go to Console tab",
            "4. Paste the script below and press Enter",
            "5. Review the form and submit manually"
        ]
    }
class ResumeEditRequest(BaseModel):
    """Request body for refining a resume."""
    prompt: str


@router.get("/{draft_id}/resume/versions", response_model=List[ResumeVersion])
async def get_resume_versions(draft_id: str):
    """Get all resume versions for a draft."""
    return draft_manager.get_resume_versions(draft_id)


@router.post("/{draft_id}/resume/versions")
async def refine_resume(draft_id: str, request: ResumeEditRequest, background_tasks: BackgroundTasks):
    """
    Generate a new version of the resume based on user prompt.
    """
    from src.services import DraftPreparationService
    from src.job_manager import JobManager
    from src.resume_builder import ResumeBuilder
    from src.agent import BrowserAgent
    
    draft = draft_manager.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
        
    versions = draft_manager.get_resume_versions(draft_id)
    if not versions:
        raise HTTPException(status_code=400, detail="No base version found to refine")
        
    # Get the latest/current version to refine from
    current_version = next((v for v in versions if v.is_current), versions[0])
    new_version_num = max(v.version_number for v in versions) + 1
    
    # Initialize service
    service = DraftPreparationService(
        job_manager=JobManager(),
        browser_agent=BrowserAgent(),
        resume_builder=ResumeBuilder(),
        draft_manager=draft_manager
    )
    
    refinement_prompt = f"""
    USER REFINEMENT INSTRUCTIONS:
    {request.prompt}
    
    Please incorporate these instructions while maintaining the quality and structure.
    """
    
    # Create version entry first with GENERATING status
    import uuid
    version_id = str(uuid.uuid4())
    
    # Use accurate job ID from URL
    from src.url_utils import get_stable_job_id
    job_id = get_stable_job_id(draft.job_url)

    # Add build task to background
    background_tasks.add_task(
        service.resume_builder.build,
        job_description=draft.job_details,
        user_profile_text=get_user_profile_text(), # Use actual profile text
        job_id=job_id,
        template_path=current_version.tex_path,
        tailoring_prompt=refinement_prompt,
        version=f"v{new_version_num}",
        version_id=version_id,
        draft_manager=draft_manager,
        job_manager=service.job_manager,
        job_url=draft.job_url
    )
    
    # Define predicted paths
    tex_path = f"data/tex_resumes/{job_id}/v{new_version_num}/Resume_{job_id}_v{new_version_num}.tex"
    pdf_path = f"data/generated_resumes/{job_id}/v{new_version_num}/Resume_{job_id}_v{new_version_num}.pdf"
    
    # Create the record in DB (status will be GENERATING because PDF is still cooking)
    new_v = ResumeVersion(
        id=version_id,
        draft_id=draft_id,
        version_number=new_version_num,
        tex_path=tex_path,
        pdf_path=pdf_path,
        ats_score=0, # Score can be updated after PDF text extraction if needed
        justification="Generating...",
        keywords_added="",
        changes_summary=request.prompt,
        status="GENERATING",
        is_current=True
    )
    draft_manager.create_resume_version(new_v)
    return new_v


@router.post("/{draft_id}/resume/use_original")
async def use_original_resume(draft_id: str):
    """Adds the user's original uploaded PDF as a new resume version."""
    draft = draft_manager.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
        
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    
    orig_path = pm.get_current_resume_path("pdf")
    if not orig_path or not os.path.exists(orig_path):
        raise HTTPException(status_code=400, detail="No original PDF resume uploaded in profile")
        
    versions = draft_manager.get_resume_versions(draft_id)
    new_version_num = max(v.version_number for v in versions) + 1 if versions else 1
    
    # Store as a new version
    import uuid
    new_v = ResumeVersion(
        id=str(uuid.uuid4()),
        draft_id=draft_id,
        version_number=new_version_num,
        tex_path="", # No TeX for original
        pdf_path=orig_path,
        ats_score=0, # Could trigger re-calc later
        justification="User's original upload",
        changes_summary="Original Un-tailored Resume",
        status="COMPLETED",
        is_current=True
    )
    draft_manager.create_resume_version(new_v)
    return new_v


@router.post("/{draft_id}/resume/versions/{version_id}/select")
async def select_resume_version(draft_id: str, version_id: str):
    """Set a specific version as current."""
    success = draft_manager.set_current_resume_version(draft_id, version_id)
    if not success:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"status": "success"}


@router.get("/{draft_id}/resume/preview")
async def preview_resume(draft_id: str, version_id: Optional[str] = None):
    """
    Stream the PDF for preview.
    If version_id is not provided, use the current version.
    """
    if version_id:
        versions = draft_manager.get_resume_versions(draft_id)
        version = next((v for v in versions if v.id == version_id), None)
    else:
        versions = draft_manager.get_resume_versions(draft_id)
        version = next((v for v in versions if v.is_current), None)
        
    if not version or not version.pdf_path:
        # Fallback to draft.resume_path
        draft = draft_manager.get_draft(draft_id)
        if draft and draft.resume_path and os.path.exists(draft.resume_path):
            return FileResponse(draft.resume_path, media_type="application/pdf")
        raise HTTPException(status_code=404, detail="Resume not found")
        
    if not os.path.exists(version.pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF file not found at {version.pdf_path}")
        
    return FileResponse(version.pdf_path, media_type="application/pdf")
