"""
API router for draft management endpoints.

This router provides endpoints for managing application drafts in the
draft-first workflow. Users can list, view, and open drafts for manual completion.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from src.draft_manager import DraftManager
from api.schemas.form_state import ApplicationDraft, DraftSummary, DraftStatus

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
        if field.value:
            escaped_value = field.value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            fields_js.append(f"""
    // {field.label or field.field_id}
    fillField("{field.field_id}", '{escaped_value}');""")
    
    script = f"""
// AutoApply Form Filler - Draft: {draft_id}
// Paste this in your browser console (F12) on the job application page

(function() {{
    function fillField(fieldId, value) {{
        const selectors = [
            '#' + fieldId,
            '[name="' + fieldId + '"]',
            '[id="' + fieldId + '"]',
            '[data-field="' + fieldId + '"]'
        ];
        
        for (const selector of selectors) {{
            try {{
                const el = document.querySelector(selector);
                if (el) {{
                    el.focus();
                    el.value = value;
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    console.log('✅ Filled: ' + fieldId);
                    return true;
                }}
            }} catch (e) {{}}
        }}
        console.log('❌ Not found: ' + fieldId);
        return false;
    }}
    
    console.log('🚀 AutoApply filling {len(draft.form_state.fields)} fields...');
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

