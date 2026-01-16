"""Tests for resume upload and profile management functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.services import DraftPreparationService


class TestDraftPreparationWithResume:
    """Tests for DraftPreparationService resume handling."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for DraftPreparationService."""
        return {
            "job_manager": MagicMock(),
            "browser_agent": AsyncMock(),
            "resume_builder": MagicMock()
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create a DraftPreparationService with mocked dependencies."""
        deps = mock_dependencies
        deps["browser_agent"].scrape_job_details.return_value = {
            "job_description": "Test job description",
            "apply_link": "https://example.com/apply",
            "company_name": "Test Corp",
            "job_title": "Engineer"
        }
        deps["browser_agent"].extract_form.return_value = {
            "status": "extracted",
            "fields": []
        }
        deps["resume_builder"].build = AsyncMock(return_value=(
            "/path/to/resume.pdf",
            "/path/to/resume.tex",
            ["Python"],
            "Initial"
        ))
        deps["resume_builder"].calculate_ats_score = AsyncMock(return_value={"score": 75})

        return DraftPreparationService(
            job_manager=deps["job_manager"],
            browser_agent=deps["browser_agent"],
            resume_builder=deps["resume_builder"]
        )

    @pytest.mark.asyncio
    async def test_prepare_draft_uses_uploaded_pdf(self, service, mock_dependencies):
        """Test that uploaded PDF resumes are used when configured."""
        with patch("src.services.ProfileManager") as MockPM:
            MockPM.return_value.get_profile.return_value = {
                "resume_generation_mode": "uploaded_pdf"
            }
            MockPM.return_value.get_current_resume_path.return_value = "/tmp/uploaded.pdf"

            with patch("os.path.exists", return_value=True):
                result = await service.prepare_draft(
                    job_link="https://example.com/job",
                    user_details_text="Test User"
                )

        assert result is not None
        # Resume builder should not be called when using uploaded PDF
        mock_dependencies["resume_builder"].build.assert_not_called()

    @pytest.mark.asyncio
    async def test_prepare_draft_falls_back_when_upload_missing(self, service, mock_dependencies):
        """Test fallback to ATS generation when uploaded file is missing."""
        with patch("src.services.ProfileManager") as MockPM:
            MockPM.return_value.get_profile.return_value = {
                "resume_generation_mode": "uploaded_pdf"
            }
            MockPM.return_value.get_current_resume_path.return_value = "/tmp/missing.pdf"

            with patch("os.path.exists", return_value=False):
                result = await service.prepare_draft(
                    job_link="https://example.com/job",
                    user_details_text="Test User"
                )

        assert result is not None
        # Should fall back to generating resume
        mock_dependencies["resume_builder"].build.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_draft_generates_ats_resume(self, service, mock_dependencies):
        """Test ATS resume generation mode."""
        with patch("src.services.ProfileManager") as MockPM:
            MockPM.return_value.get_profile.return_value = {
                "resume_generation_mode": "ats_generated"
            }
            MockPM.return_value.get_current_resume_path.return_value = None

            result = await service.prepare_draft(
                job_link="https://example.com/job",
                user_details_text="Test User"
            )

        assert result is not None
        mock_dependencies["resume_builder"].build.assert_called_once()
