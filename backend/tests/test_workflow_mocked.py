import pytest
import os
import tempfile
import shutil
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock, ANY
from src.services import JobApplicationService
from src.rss_watcher import RSSWatcher

class TestJobApplicationServiceWorkflow:
    """Tests for JobApplicationService.process_job() with mocked dependencies."""
    
    @pytest.fixture
    def mock_browser_agent(self):
        agent = AsyncMock()
        agent.scrape_job_details.return_value = "Job Title: Senior Software Engineer\nRequirements: Python"
        agent.apply_to_job.return_value = "Application submitted successfully"
        return agent
    
    @pytest.fixture
    def mock_resume_builder(self):
        builder = MagicMock()
        builder.build.return_value = "/path/to/resume.pdf"
        return builder
    
    @pytest.fixture
    def mock_job_manager(self):
        manager = MagicMock()
        return manager
    
    @pytest.fixture
    def service(self, mock_job_manager, mock_browser_agent, mock_resume_builder):
        return JobApplicationService(
            job_manager=mock_job_manager,
            browser_agent=mock_browser_agent,
            resume_builder=mock_resume_builder
        )

    @pytest.mark.asyncio
    async def test_successful_workflow(self, service, mock_browser_agent, mock_resume_builder, mock_job_manager):
        job_url = "https://example.com/job/123"
        log_messages = []
        
        result = await service.process_job(
            job_link=job_url,
            user_details_text="Test User",
            log_callback=lambda msg: log_messages.append(msg)
        )
        
        assert result is True
        mock_browser_agent.scrape_job_details.assert_called_once_with(job_url)
        mock_resume_builder.build.assert_called_once()
        mock_browser_agent.apply_to_job.assert_called_once()
        assert mock_job_manager.update_job.call_count >= 4
        assert any("Completed" in str(args) for args in mock_job_manager.update_job.call_args_list)

    @pytest.mark.asyncio
    async def test_scraping_failure(self, service, mock_browser_agent, mock_job_manager):
        mock_browser_agent.scrape_job_details.side_effect = Exception("Browser timeout")
        job_url = "https://example.com/job/456"
        
        result = await service.process_job(job_url, "user details")
        
        assert result is False
        mock_job_manager.update_job.assert_any_call(job_url, status="Failed", error_message="Browser timeout")


class TestRunAutoApplyLoop:
    """Tests for the run_auto_apply() main loop logic with the new RSSWatcher."""
    
    @pytest.mark.asyncio
    @patch('src.main.ResumeBuilder')
    @patch('src.main.BrowserAgent')
    @patch('src.main.JobManager')
    @patch('src.main.ConfigManager')
    @patch('src.main.ProfileManager')
    @patch('src.main.RSSWatcher')
    @patch('src.main.JobApplicationService')
    async def test_single_run_orchestration(
        self, 
        MockService, 
        MockWatcher, 
        MockProfile, 
        MockConfig, 
        MockJobManager, 
        MockBrowser, 
        MockResume
    ):
        from src.main import run_auto_apply
        
        # Setup mocks
        mock_job_manager = MockJobManager.return_value
        mock_job_manager.get_all_jobs.return_value = [
            {"url": "https://p.com/1", "status": "Pending"}
        ]
        
        mock_watcher = MockWatcher.return_value
        mock_watcher.poll_once = AsyncMock()
        
        mock_service = MockService.return_value
        mock_service.process_job = AsyncMock(return_value=True)
        
        await run_auto_apply(continuous=False)
        
        # Verify watcher was polled
        mock_watcher.poll_once.assert_called_once()
        
        # Verify pending job was processed
        mock_service.process_job.assert_called_once_with(
            job_link="https://p.com/1",
            user_details_text=MockProfile.return_value.get_profile_as_text.return_value,
            log_callback=ANY
        )
