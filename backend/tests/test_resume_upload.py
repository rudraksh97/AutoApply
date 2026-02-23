"""Tests for resume upload and profile management functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch




class TestDraftPreparationWithResume:
    """Tests for DraftPreparationService resume handling."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for DraftPreparationService."""
        return {
            "job_manager": MagicMock(),
            "browser_agent": AsyncMock(),
            "resume_builder": MagicMock(),
            "profile_service": MagicMock()
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create a DraftPreparationService with mocked dependencies."""
        from src.services import DraftPreparationService
        deps = mock_dependencies
        deps["browser_agent"].scrape_job_details.return_value = {
            "job_description": "Test job description",
            "apply_link": "https://example.com/apply",
            "job_title": "Engineer"
        }
        deps["browser_agent"].extract_form.return_value = {
            "status": "extracted",
            "fields": [
                {"name": "first_name", "type": "text", "label": "First Name"},
                {"name": "last_name", "type": "text", "label": "Last Name"},
                {"name": "email", "type": "email", "label": "Email"}
            ]
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
            resume_builder=deps["resume_builder"],
            profile_service=deps["profile_service"]
        )

    @pytest.mark.asyncio
    async def test_prepare_draft_uses_uploaded_pdf(self, service, mock_dependencies):
        """Test that uploaded PDF resumes are used when configured."""
        mock_dependencies["profile_service"].get_profile.return_value = {
            "resume_generation_mode": "uploaded_pdf",
            "pdf_resumes": [{"id": "res-1", "path": "/tmp/uploaded.pdf"}],
            "current_pdf_resume_id": "res-1"
        }

        with patch("os.path.exists", return_value=True):
            result = await service.prepare_draft(
                job_link="https://example.com/job",
                user_id="test-user"
            )

        assert result is not None
        # Resume builder should not be called when using uploaded PDF
        mock_dependencies["resume_builder"].build.assert_not_called()

    @pytest.mark.asyncio
    async def test_prepare_draft_falls_back_when_upload_missing(self, service, mock_dependencies):
        """Test fallback to ATS generation when uploaded file is missing."""
        mock_dependencies["profile_service"].get_profile.return_value = {
            "resume_generation_mode": "uploaded_pdf",
            "pdf_resumes": [{"id": "res-1", "path": "/tmp/missing.pdf"}],
            "current_pdf_resume_id": "res-1"
        }

        with patch("os.path.exists", return_value=False):
            result = await service.prepare_draft(
                job_link="https://example.com/job",
                user_id="test-user"
            )

        assert result is not None
        # Should fall back to generating resume
        mock_dependencies["resume_builder"].build.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_draft_generates_ats_resume(self, service, mock_dependencies):
        """Test ATS resume generation mode."""
        mock_dependencies["profile_service"].get_profile.return_value = {
            "resume_generation_mode": "ats_generated"
        }

        result = await service.prepare_draft(
            job_link="https://example.com/job",
            user_id="test-user"
        )

        assert result is not None
        mock_dependencies["resume_builder"].build.assert_called_once()
