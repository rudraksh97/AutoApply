import pytest
from unittest.mock import MagicMock, AsyncMock
from src.services import JobApplicationService

@pytest.mark.asyncio
async def test_process_job_success():
    # Arrange
    mock_job_manager = MagicMock()
    mock_browser_agent = AsyncMock()
    mock_resume_builder = MagicMock()
    
    # Mock return values
    mock_browser_agent.scrape_job_details.return_value = "Extracted Job Description"
    mock_resume_builder.build.return_value = "/path/to/resume.pdf"
    mock_browser_agent.apply_to_job.return_value = "Success"
    
    service = JobApplicationService(
        job_manager=mock_job_manager,
        browser_agent=mock_browser_agent,
        resume_builder=mock_resume_builder
    )
    
    # Act
    result = await service.process_job(
        job_link="https://example.com/job",
        user_details_text="User Info",
        log_callback=lambda x: None
    )
    
    # Assert
    assert result is True
    # Verify sequence of updates
    mock_job_manager.update_job.assert_any_call("https://example.com/job", status="Running - Scraping")
    mock_job_manager.update_job.assert_any_call("https://example.com/job", details="Extracted Job Description...")
    mock_job_manager.update_job.assert_any_call("https://example.com/job", status="Completed")
    
    # Verify browser agent calls
    mock_browser_agent.scrape_job_details.assert_called_once_with("https://example.com/job")
    mock_browser_agent.apply_to_job.assert_called_once_with("https://example.com/job", "/path/to/resume.pdf", "User Info")

@pytest.mark.asyncio
async def test_process_job_failure_in_scraping():
    # Arrange
    mock_job_manager = MagicMock()
    mock_browser_agent = AsyncMock()
    mock_resume_builder = MagicMock()
    
    mock_browser_agent.scrape_job_details.side_effect = Exception("Scraping failed")
    
    service = JobApplicationService(
        job_manager=mock_job_manager,
        browser_agent=mock_browser_agent,
        resume_builder=mock_resume_builder
    )
    
    # Act
    result = await service.process_job(
        job_link="https://example.com/job",
        user_details_text="User Info",
        log_callback=lambda x: None
    )
    
    # Assert
    assert result is False
    mock_job_manager.update_job.assert_any_call(
        "https://example.com/job", 
        status="Failed", 
        error_message="Scraping failed"
    )
