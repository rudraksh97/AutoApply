
import os
import pytest
import asyncio
from src.agent import BrowserAgent
from src.profile_manager import ProfileManager

@pytest.mark.asyncio
async def test_visual_apply():
    """
    Visual test for applying to a job.
    
    Requires environment variables:
    - TEST_JOB_LINK: URL of the job to apply to.
    - TEST_RESUME_PATH: Path to the resume PDF to use.
    
    If these are not present, the test is skipped.
    """
    # Hardcoded values for manual testing
    job_link = "https://jobs.ashbyhq.com/Framenergy/d8b6bae9-cd1b-4dea-8d98-168dad8f2294/application"
    resume_path = os.path.abspath("tests/my_resume")

    if not os.path.exists(resume_path):
        os.makedirs(resume_path, exist_ok=True)
        print(f"Created directory: {resume_path}. Please put your resume there.")

    # Handle directory input
    if os.path.isdir(resume_path):
        found = False
        for root, _, files in os.walk(resume_path):
            for file in files:
                if file.lower().endswith(('.pdf', '.tex')):
                    resume_path = os.path.join(root, file)
                    found = True
                    break
            if found: break
        
        if not found:
            pytest.fail(f"No .pdf or .tex file found in directory: {resume_path}")
    
    print(f"Using Resume: {resume_path}")

    # 1. Initialize Agent in HEADED mode (headless=False)
    agent = BrowserAgent(headless=False)
    
    # 2. Get User Details
    pm = ProfileManager()
    user_details = pm.get_profile_as_text()
    
    print(f"\n[DEBUG] User Details sent to Agent:\n{user_details}\n")
    
    print(f"\n[VISUAL TEST] Starting Application...")
    print(f"Job: {job_link}")
    print(f"Resume: {resume_path}")
    print("Watch the browser window...")
    
    # 3. Run Application
    result = await agent.apply_to_job(job_link, resume_path, user_details)
    
    print(f"[VISUAL TEST] Result: {result}")
    assert result is not None, "Agent returned None result"
