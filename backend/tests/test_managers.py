"""
Unit tests for JobManager, ProfileManager, and ConfigManager.

These tests use temp directories to isolate from production data.
No external dependencies (LLM, browser) required.
"""
import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch


class TestJobManager:
    """Unit tests for JobManager CRUD operations."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temp directory for test data (kept for non-DB file tests if any)."""
        temp_dir = tempfile.mkdtemp()
        data_dir = os.path.join(temp_dir, "data")
        os.makedirs(data_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def job_manager(self, db_session):
        """Create a JobManager using test DB via patched SessionLocal."""
        from src.job_manager import JobManager
        # Ensure we pass user_id in tests or update tests to simulate user
        manager = JobManager()
        yield manager

    def test_add_job(self, job_manager, test_user):
        """Test adding a new job."""
        user_id = test_user.id
        result = job_manager.add_job("https://example.com/job1", user_id=user_id, status="PENDING")
        assert result is True
        
        jobs = job_manager.get_all_jobs(user_id=user_id)
        assert len(jobs) == 1
        assert jobs[0]["url"] == "https://example.com/job1"
        assert jobs[0]["status"] == "PENDING"
    
    def test_add_duplicate_job(self, job_manager, test_user):
        """Test that duplicate jobs are rejected."""
        job_manager.add_job("https://example.com/job1", user_id=test_user.id)
        result = job_manager.add_job("https://example.com/job1", user_id=test_user.id)
        assert result is False
        
        jobs = job_manager.get_all_jobs(user_id=test_user.id)
        assert len(jobs) == 1
    
    def test_job_exists(self, job_manager, test_user):
        """Test job existence check."""
        assert job_manager.job_exists("https://example.com/job1", user_id=test_user.id) is False
        job_manager.add_job("https://example.com/job1", user_id=test_user.id)
        assert job_manager.job_exists("https://example.com/job1", user_id=test_user.id) is True
    
    def test_update_job_status(self, job_manager, test_user):
        """Test updating job status."""
        job_manager.add_job("https://example.com/job1", user_id=test_user.id)
        
        result = job_manager.update_job("https://example.com/job1", user_id=test_user.id, status="Running - Scraping")
        assert result is True
        
        jobs = job_manager.get_all_jobs(user_id=test_user.id)
        assert jobs[0]["status"] == "Running - Scraping"
    
    def test_update_job_with_pdf(self, job_manager, test_user):
        """Test updating job with PDF path."""
        job_manager.add_job("https://example.com/job1", user_id=test_user.id)
        
        job_manager.update_job("https://example.com/job1", user_id=test_user.id, pdf_path="/path/to/resume.pdf")
        
        jobs = job_manager.get_all_jobs(user_id=test_user.id)
        assert jobs[0]["pdf_path"] == "/path/to/resume.pdf"
    
    def test_update_job_with_error(self, job_manager, test_user):
        """Test updating job with error message."""
        job_manager.add_job("https://example.com/job1", user_id=test_user.id)
        
        job_manager.update_job("https://example.com/job1", user_id=test_user.id, status="Failed", error_message="Connection timeout")
        
        jobs = job_manager.get_all_jobs(user_id=test_user.id)
        assert jobs[0]["status"] == "Failed"
        assert jobs[0]["error_message"] == "Connection timeout"
    
    def test_update_nonexistent_job(self, job_manager, test_user):
        """Test updating a job that doesn't exist."""
        result = job_manager.update_job("https://nonexistent.com/job", user_id=test_user.id, status="Running")
        assert result is False
