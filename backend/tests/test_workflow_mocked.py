"""
Mocked integration tests for the job application workflow.

Tests the full pipeline logic without real browser/LLM dependencies.
Fast and reliable for CI/CD.
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestProcessJobWorkflow:
    """Tests for process_job() workflow with mocked dependencies."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create temp directory for test data."""
        temp_dir = tempfile.mkdtemp()
        data_dir = os.path.join(temp_dir, "data")
        os.makedirs(data_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_browser_agent(self):
        """Create a mock BrowserAgent."""
        agent = Mock()
        agent.scrape_job_details = AsyncMock(return_value="""
            Job Title: Senior Software Engineer
            
            Requirements:
            - 5+ years Python experience
            - Experience with AWS, Docker, Kubernetes
            - Strong communication skills
            
            Responsibilities:
            - Design and build scalable systems
            - Mentor junior engineers
        """)
        agent.apply_to_job = AsyncMock(return_value="Application submitted successfully")
        return agent
    
    @pytest.fixture
    def mock_resume_builder(self, temp_data_dir):
        """Create a mock ResumeBuilder."""
        builder = Mock()
        fake_pdf = os.path.join(temp_data_dir, "data", "Resume_12345.pdf")
        with open(fake_pdf, 'w') as f:
            f.write("FAKE PDF")
        builder.build = Mock(return_value=fake_pdf)
        return builder
    
    @pytest.fixture
    def mock_job_manager(self):
        """Create a mock JobManager that tracks state."""
        manager = Mock()
        manager.jobs = {}
        
        def update_job(url, status=None, pdf_path=None, details=None, error_message=None):
            if url not in manager.jobs:
                manager.jobs[url] = {}
            if status:
                manager.jobs[url]['status'] = status
            if pdf_path:
                manager.jobs[url]['pdf_path'] = pdf_path
            if details:
                manager.jobs[url]['details'] = details
            if error_message is not None:
                manager.jobs[url]['error_message'] = error_message
            return True
        
        manager.update_job = Mock(side_effect=update_job)
        return manager
    
    @pytest.mark.asyncio
    async def test_successful_workflow(self, mock_browser_agent, mock_resume_builder, mock_job_manager):
        """Test successful job processing workflow."""
        from src.main import process_job
        
        job_url = "https://example.com/job/123"
        user_details = "Name: Test User\nEmail: test@example.com"
        log_messages = []
        
        result = await process_job(
            job_link=job_url,
            resume_builder=mock_resume_builder,
            browser_agent=mock_browser_agent,
            job_manager=mock_job_manager,
            user_details_text=user_details,
            log_callback=lambda msg: log_messages.append(msg)
        )
        
        # Verify success
        assert result is True
        
        # Verify workflow steps executed
        mock_browser_agent.scrape_job_details.assert_called_once_with(job_url)
        mock_resume_builder.build.assert_called_once()
        mock_browser_agent.apply_to_job.assert_called_once()
        
        # Verify status updates
        assert mock_job_manager.update_job.call_count >= 4  # Multiple status updates
        assert mock_job_manager.jobs[job_url]['status'] == 'Completed'
        
        # Verify log messages
        assert any("Processing Job" in msg for msg in log_messages)
        assert any("Scraping" in msg for msg in log_messages)
    
    @pytest.mark.asyncio
    async def test_scraping_failure(self, mock_browser_agent, mock_resume_builder, mock_job_manager):
        """Test workflow when scraping fails."""
        from src.main import process_job
        
        mock_browser_agent.scrape_job_details = AsyncMock(side_effect=Exception("Browser timeout"))
        
        job_url = "https://example.com/job/456"
        log_messages = []
        
        result = await process_job(
            job_link=job_url,
            resume_builder=mock_resume_builder,
            browser_agent=mock_browser_agent,
            job_manager=mock_job_manager,
            user_details_text="user details",
            log_callback=lambda msg: log_messages.append(msg)
        )
        
        # Verify failure
        assert result is False
        
        # Verify job marked as failed
        assert mock_job_manager.jobs[job_url]['status'] == 'Failed'
        assert 'Browser timeout' in mock_job_manager.jobs[job_url]['error_message']
        
        # Resume building should not be called
        mock_resume_builder.build.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_resume_building_failure(self, mock_browser_agent, mock_resume_builder, mock_job_manager):
        """Test workflow when resume building fails."""
        from src.main import process_job
        
        mock_resume_builder.build = Mock(side_effect=Exception("LaTeX compilation error"))
        
        job_url = "https://example.com/job/789"
        log_messages = []
        
        result = await process_job(
            job_link=job_url,
            resume_builder=mock_resume_builder,
            browser_agent=mock_browser_agent,
            job_manager=mock_job_manager,
            user_details_text="user details",
            log_callback=lambda msg: log_messages.append(msg)
        )
        
        # Verify failure
        assert result is False
        
        # Scraping should have completed
        mock_browser_agent.scrape_job_details.assert_called_once()
        
        # Apply should not be called
        mock_browser_agent.apply_to_job.assert_not_called()
        
        # Job should be failed
        assert mock_job_manager.jobs[job_url]['status'] == 'Failed'
    
    @pytest.mark.asyncio
    async def test_application_failure(self, mock_browser_agent, mock_resume_builder, mock_job_manager):
        """Test workflow when application submission fails."""
        from src.main import process_job
        
        mock_browser_agent.apply_to_job = AsyncMock(side_effect=Exception("Form submission failed"))
        
        job_url = "https://example.com/job/999"
        log_messages = []
        
        result = await process_job(
            job_link=job_url,
            resume_builder=mock_resume_builder,
            browser_agent=mock_browser_agent,
            job_manager=mock_job_manager,
            user_details_text="user details",
            log_callback=lambda msg: log_messages.append(msg)
        )
        
        # Verify failure
        assert result is False
        
        # All prior steps should have completed
        mock_browser_agent.scrape_job_details.assert_called_once()
        mock_resume_builder.build.assert_called_once()
        
        # Job should be failed
        assert mock_job_manager.jobs[job_url]['status'] == 'Failed'
        assert 'Form submission failed' in mock_job_manager.jobs[job_url]['error_message']


class TestRunAutoApplyLoop:
    """Tests for the run_auto_apply() main loop logic."""
    
    @pytest.mark.asyncio
    async def test_single_run_no_jobs(self):
        """Test single run with no pending jobs."""
        from src.main import run_auto_apply
        
        log_messages = []
        
        with patch('src.main.ResumeBuilder') as MockResumeBuilder, \
             patch('src.main.BrowserAgent') as MockBrowserAgent, \
             patch('src.main.ConfigManager') as MockConfigManager, \
             patch('src.main.JobManager') as MockJobManager, \
             patch('src.main.ProfileManager') as MockProfileManager, \
             patch('src.main.RSSWatcher') as MockRSSWatcher:
            
            # Setup mocks
            mock_config = Mock()
            mock_config.get_feeds.return_value = []
            MockConfigManager.return_value = mock_config
            
            mock_job_mgr = Mock()
            mock_job_mgr.get_all_jobs.return_value = []
            MockJobManager.return_value = mock_job_mgr
            
            mock_profile = Mock()
            mock_profile.get_profile_as_text.return_value = "Test User"
            MockProfileManager.return_value = mock_profile
            
            mock_watcher = Mock()
            mock_watcher.get_new_jobs.return_value = iter([])  # Empty generator
            MockRSSWatcher.return_value = mock_watcher
            
            await run_auto_apply(
                log_callback=lambda msg: log_messages.append(msg),
                continuous=False
            )
            
            assert any("Checking for new jobs" in msg for msg in log_messages)
            assert any("No pending jobs" in msg for msg in log_messages)
    
    @pytest.mark.asyncio
    async def test_single_run_with_pending_job(self):
        """Test single run with a pending job."""
        from src.main import run_auto_apply
        
        log_messages = []
        
        with patch('src.main.ResumeBuilder') as MockResumeBuilder, \
             patch('src.main.BrowserAgent') as MockBrowserAgent, \
             patch('src.main.ConfigManager') as MockConfigManager, \
             patch('src.main.JobManager') as MockJobManager, \
             patch('src.main.ProfileManager') as MockProfileManager, \
             patch('src.main.RSSWatcher') as MockRSSWatcher, \
             patch('src.main.process_job', new_callable=AsyncMock) as mock_process:
            
            mock_process.return_value = True
            
            MockConfigManager.return_value.get_feeds.return_value = []
            
            mock_job_mgr = Mock()
            mock_job_mgr.get_all_jobs.return_value = [
                {"url": "https://example.com/job1", "status": "Pending"}
            ]
            MockJobManager.return_value = mock_job_mgr
            
            MockProfileManager.return_value.get_profile_as_text.return_value = "Test"
            
            mock_watcher = Mock()
            mock_watcher.get_new_jobs.return_value = iter([])
            MockRSSWatcher.return_value = mock_watcher
            
            await run_auto_apply(
                log_callback=lambda msg: log_messages.append(msg),
                continuous=False
            )
            
            # process_job should be called for pending job
            mock_process.assert_called_once()
            assert any("Processing 1 pending jobs" in msg for msg in log_messages)


class TestJobStateTransitions:
    """Tests for job status transitions through the workflow."""
    
    @pytest.mark.asyncio
    async def test_status_transitions_on_success(self):
        """Verify correct status transitions for successful job."""
        from src.main import process_job
        
        status_history = []
        
        mock_job_mgr = Mock()
        def track_update(url, status=None, **kwargs):
            if status:
                status_history.append(status)
            return True
        mock_job_mgr.update_job = Mock(side_effect=track_update)
        
        mock_agent = Mock()
        mock_agent.scrape_job_details = AsyncMock(return_value="Job description")
        mock_agent.apply_to_job = AsyncMock(return_value="Success")
        
        mock_builder = Mock()
        mock_builder.build = Mock(return_value="/path/to/resume.pdf")
        
        await process_job(
            job_link="https://example.com/job",
            resume_builder=mock_builder,
            browser_agent=mock_agent,
            job_manager=mock_job_mgr,
            user_details_text="details",
            log_callback=lambda x: None
        )
        
        # Verify status progression
        expected_order = ["Running - Scraping", "Running - Generating Resume", "Running - Resume Ready", "Running - Applying", "Completed"]
        assert status_history == expected_order
    
    @pytest.mark.asyncio
    async def test_status_transitions_on_failure(self):
        """Verify correct status transitions when job fails."""
        from src.main import process_job
        
        status_history = []
        
        mock_job_mgr = Mock()
        def track_update(url, status=None, **kwargs):
            if status:
                status_history.append(status)
            return True
        mock_job_mgr.update_job = Mock(side_effect=track_update)
        
        mock_agent = Mock()
        mock_agent.scrape_job_details = AsyncMock(side_effect=Exception("Network error"))
        
        mock_builder = Mock()
        
        await process_job(
            job_link="https://example.com/job",
            resume_builder=mock_builder,
            browser_agent=mock_agent,
            job_manager=mock_job_mgr,
            user_details_text="details",
            log_callback=lambda x: None
        )
        
        # Should transition to Running, then Failed
        assert "Running - Scraping" in status_history
        assert "Failed" in status_history
        assert "Completed" not in status_history
