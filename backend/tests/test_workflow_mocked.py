"""Unit tests for DraftPreparationService with mocked dependencies."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY

from src.services import DraftPreparationService


class TestDraftPreparationServiceWorkflow:
    """Tests for DraftPreparationService.prepare_draft() with mocked dependencies."""

    @pytest.fixture
    def mock_browser_agent(self):
        """Create a mock browser agent with standard responses."""
        agent = AsyncMock()
        agent.scrape_job_details.return_value = {
            "job_description": "Senior Software Engineer\nRequirements: Python",
            "apply_link": "https://example.com/job/123/apply",
            "company_name": "Example Corp",
            "job_title": "Senior Software Engineer"
        }
        agent.extract_form.return_value = {
            "status": "extracted",
            "fields": []
        }
        return agent

    @pytest.fixture
    def mock_resume_builder(self):
        """Create a mock resume builder."""
        builder = MagicMock()
        builder.build = AsyncMock(return_value=(
            "/path/to/resume.pdf",
            "/path/to/resume.tex",
            ["Python"],
            "Initial"
        ))
        builder.calculate_ats_score = AsyncMock(return_value={"score": 75})
        return builder

    @pytest.fixture
    def mock_job_manager(self):
        """Create a mock job manager."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_job_manager, mock_browser_agent, mock_resume_builder):
        """Create a DraftPreparationService with mocked dependencies."""
        return DraftPreparationService(
            job_manager=mock_job_manager,
            browser_agent=mock_browser_agent,
            resume_builder=mock_resume_builder
        )

    @pytest.fixture
    def mock_profile(self):
        """Create a mock ProfileManager context."""
        with patch("src.services.ProfileManager") as MockPM:
            MockPM.return_value.get_profile.return_value = {
                "resume_generation_mode": "ats_generated"
            }
            MockPM.return_value.get_current_resume_path.return_value = None
            yield MockPM

    @pytest.mark.asyncio
    async def test_successful_workflow(self, service, mock_browser_agent, mock_profile):
        """Test that prepare_draft succeeds with valid inputs."""
        job_url = "https://example.com/job/123"

        result = await service.prepare_draft(
            job_link=job_url,
            user_details_text="Test User"
        )

        assert result is not None
        mock_browser_agent.scrape_job_details.assert_called_once_with(job_url)
        mock_browser_agent.extract_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_scraping_failure(self, service, mock_browser_agent, mock_job_manager):
        """Test that scraping errors are handled gracefully."""
        mock_browser_agent.scrape_job_details.side_effect = Exception("Browser timeout")
        job_url = "https://example.com/job/456"

        with patch("src.services.ProfileManager"):
            result = await service.prepare_draft(job_url, "user details")

        assert result is None
        mock_job_manager.update_job.assert_any_call(
            job_url,
            status="Draft Failed",
            error_message="Browser timeout"
        )


class TestRunAutoApplyLoop:
    """Tests for the run_auto_apply() main loop."""

    @pytest.mark.asyncio
    @patch('src.main.ResumeBuilder')
    @patch('src.main.BrowserAgent')
    @patch('src.main.JobManager')
    @patch('src.main.ConfigManager')
    @patch('src.main.ProfileManager')
    @patch('src.main.RSSWatcher')
    @patch('src.main.DraftPreparationService')
    async def test_single_run_orchestration(
        self,
        MockService,
        MockWatcher,
        MockProfile,
        _MockConfig,
        MockJobManager,
        _MockBrowser,
        _MockResume
    ):
        """Test that a single run polls RSS and processes pending jobs."""
        from src.main import run_auto_apply

        # Setup job manager mock
        mock_job_manager = MockJobManager.return_value
        mock_job_manager.get_all_jobs.return_value = [
            {"url": "https://example.com/job/1", "status": "Pending"}
        ]

        # Setup watcher mock
        mock_watcher = MockWatcher.return_value
        mock_watcher.poll_once = AsyncMock()

        # Setup service mock
        mock_service = MockService.return_value
        mock_service.prepare_draft = AsyncMock(return_value="draft-123")

        await run_auto_apply(continuous=False)

        mock_watcher.poll_once.assert_called_once()
        mock_service.prepare_draft.assert_called_once_with(
            job_link="https://example.com/job/1",
            user_details_text=MockProfile.return_value.get_profile_as_text.return_value,
            log_callback=ANY
        )
