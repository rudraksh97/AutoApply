"""
Integration test for the AutoApply job workflow.

This test triggers the REAL job application workflow using the Ashby job URL.
It uses the actual BrowserAgent, ResumeBuilder, and other components.

Requirements:
- OPENROUTER_API_KEY environment variable set
- Playwright browsers installed (run: playwright install)
- All dependencies from requirements.txt installed
"""
import pytest
import asyncio
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Test configuration - the Ashby job URL to test with
TEST_JOB_URL = "https://jobs.ashbyhq.com/Pear-VC/515c6a00-305f-4ed2-a028-cb36136d624a"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class TestJobWorkflowIntegration:
    """Integration tests using the REAL workflow components."""
    
    @pytest.fixture
    def browser_agent(self):
        """Create a real browser agent."""
        from src.agent import BrowserAgent
        return BrowserAgent(headless=True)
    
    @pytest.fixture
    def resume_builder(self):
        """Create a real resume builder."""
        from src.resume_builder import ResumeBuilder
        return ResumeBuilder()
    
    @pytest.fixture
    def job_manager(self):
        """Create a real job manager."""
        from src.job_manager import JobManager
        return JobManager()
    
    @pytest.fixture
    def profile_manager(self):
        """Create a real profile manager."""
        from src.profile_manager import ProfileManager
        return ProfileManager()
    
    @pytest.mark.asyncio
    async def test_scrape_ashby_job_details(self, browser_agent):
        """
        Test scraping job details from the Ashby job posting.
        
        This test actually opens a browser and scrapes the job page.
        """
        print(f"\n🔍 Scraping job details from: {TEST_JOB_URL}")
        
        result = await browser_agent.scrape_job_details(TEST_JOB_URL)
        
        print(f"\n📄 Scraped content (first 500 chars):\n{result[:500] if result else 'None'}...")
        
        assert result is not None, "Job details should not be None"
        assert len(result) > 0, "Job details should not be empty"
    
    @pytest.mark.asyncio
    async def test_full_job_workflow(self, browser_agent, resume_builder, job_manager, profile_manager):
        """
        Test the complete job application workflow with the Ashby link.
        
        This runs the FULL pipeline:
        1. Scrape job details
        2. Generate tailored resume
        3. (Optionally) Apply to job
        """
        from src.main import process_job
        
        user_details = profile_manager.get_profile_as_text()
        log_messages = []
        
        def log_callback(msg):
            print(f"📋 {msg}")
            log_messages.append(msg)
        
        print(f"\n🚀 Starting full workflow for: {TEST_JOB_URL}")
        
        result = await process_job(
            job_link=TEST_JOB_URL,
            resume_builder=resume_builder,
            browser_agent=browser_agent,
            job_manager=job_manager,
            user_details_text=user_details,
            log_callback=log_callback
        )
        
        print(f"\n✅ Workflow completed with result: {result}")
        print(f"📝 Log messages: {log_messages}")
        
        # The workflow should complete (either success or handled failure)
        assert result in [True, False], "Workflow should return a boolean result"
        assert len(log_messages) > 0, "Workflow should produce log messages"


class TestScrapeOnly:
    """Test just the scraping functionality - lighter weight test."""
    
    @pytest.mark.asyncio
    async def test_scrape_job_only(self):
        """
        Minimal test that just scrapes the job page.
        Does NOT apply to the job.
        """
        from src.agent import BrowserAgent
        
        agent = BrowserAgent(headless=True)
        
        print(f"\n🔍 Testing scrape-only for: {TEST_JOB_URL}")
        
        result = await agent.scrape_job_details(TEST_JOB_URL)
        
        assert result is not None
        assert len(result) > 100, "Should scrape substantial job content"
        
        print(f"\n✅ Successfully scraped {len(result)} characters")
        print(f"📄 Preview:\n{result[:300]}...")
