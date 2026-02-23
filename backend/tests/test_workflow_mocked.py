"""Unit tests for DraftPreparationService with mocked dependencies."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY




class TestDraftPreparationServiceWorkflow:
    """Tests for DraftPreparationService.prepare_draft() with mocked dependencies."""

    @pytest.fixture
    def mock_browser_agent(self):
        """Create a mock browser agent with standard responses."""
        agent = AsyncMock()
        agent.scrape_job_details.return_value = {
            "job_description": "Senior Software Engineer\nRequirements: Python",
            "apply_link": "https://example.com/job/123/apply",
            "job_title": "Senior Software Engineer"
        }
        agent.extract_form.return_value = {
            "status": "extracted",
            "fields": [
                {"name": "first_name", "type": "text", "label": "First Name"},
                {"name": "last_name", "type": "text", "label": "Last Name"},
                {"name": "email", "type": "email", "label": "Email"}
            ]
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
    def mock_profile_service(self):
        """Create a mock profile service."""
        return MagicMock()

    @pytest.fixture
    def mock_draft_manager(self):
        """Create a mock draft manager."""
        mock = MagicMock()
        mock.create_draft.return_value = "test-draft-id"
        return mock

    @pytest.fixture
    def service(self, mock_browser_agent, mock_job_manager, mock_resume_builder, mock_profile_service, mock_draft_manager):
        """Create a DraftPreparationService with mocked dependencies."""
        from src.services import DraftPreparationService
        return DraftPreparationService(
            job_manager=mock_job_manager,
            browser_agent=mock_browser_agent,
            resume_builder=mock_resume_builder,
            profile_service=mock_profile_service,
            draft_manager=mock_draft_manager
        )

    @pytest.fixture
    def mock_profile(self, mock_profile_service):
        """Setup standard mock responses for profile service."""
        profile_data = {
            "basics": {"first_name": "Test", "last_name": "User", "email": "test@example.com"},
            "resume_generation_mode": "ats_generated",
            "education": [],
            "experience": [],
            "skills": [],
            "projects": [],
            "certifications": [],
            "languages": [],
            "summary": "Test Summary"
        }
        mock_profile_service.get_profile.return_value = profile_data
        return profile_data

    @pytest.mark.asyncio
    async def test_successful_workflow(self, service, mock_browser_agent, mock_profile):
        """Test that prepare_draft succeeds with valid inputs."""
        job_url = "https://example.com/job/123"

        result = await service.prepare_draft(
            job_link=job_url,
            user_id="test-user-id"
        )

        assert result is not None
        mock_browser_agent.scrape_job_details.assert_called_once_with(job_url)
        mock_browser_agent.extract_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_scraping_failure(self, service, mock_browser_agent, mock_job_manager, mock_profile):
        """Test that scraping errors are handled gracefully."""
        mock_browser_agent.scrape_job_details.side_effect = Exception("Browser timeout")
        job_url = "https://example.com/job/456"

        result = await service.prepare_draft(job_url, "test-user-id")

        assert result is None
        mock_job_manager.update_job.assert_any_call(
            job_url,
            user_id="test-user-id",
            status="FAILED",
            error_message="Browser timeout"
        )
