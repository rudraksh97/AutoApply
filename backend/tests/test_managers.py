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
        """Create a temp directory for test data."""
        temp_dir = tempfile.mkdtemp()
        data_dir = os.path.join(temp_dir, "data")
        os.makedirs(data_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def job_manager(self, temp_data_dir):
        """Create a JobManager with patched file path."""
        with patch('src.job_manager.JOBS_FILE', os.path.join(temp_data_dir, "data", "jobs.json")):
            with patch('src.job_manager.os.path.exists') as mock_exists:
                # First call for "data" dir check, second for file
                mock_exists.side_effect = [True, False]
                from src.job_manager import JobManager
                # Reset to actually use our temp path
                import src.job_manager as jm_module
                original = jm_module.JOBS_FILE
                jm_module.JOBS_FILE = os.path.join(temp_data_dir, "data", "jobs.json")
                manager = JobManager()
                yield manager
                jm_module.JOBS_FILE = original
    
    def test_add_job(self, job_manager):
        """Test adding a new job."""
        result = job_manager.add_job("https://example.com/job1")
        assert result is True
        
        jobs = job_manager.get_all_jobs()
        assert len(jobs) == 1
        assert jobs[0]["url"] == "https://example.com/job1"
        assert jobs[0]["status"] == "Pending"
    
    def test_add_duplicate_job(self, job_manager):
        """Test that duplicate jobs are rejected."""
        job_manager.add_job("https://example.com/job1")
        result = job_manager.add_job("https://example.com/job1")
        assert result is False
        
        jobs = job_manager.get_all_jobs()
        assert len(jobs) == 1
    
    def test_job_exists(self, job_manager):
        """Test job existence check."""
        assert job_manager.job_exists("https://example.com/job1") is False
        job_manager.add_job("https://example.com/job1")
        assert job_manager.job_exists("https://example.com/job1") is True
    
    def test_update_job_status(self, job_manager):
        """Test updating job status."""
        job_manager.add_job("https://example.com/job1")
        
        result = job_manager.update_job("https://example.com/job1", status="Running - Scraping")
        assert result is True
        
        jobs = job_manager.get_all_jobs()
        assert jobs[0]["status"] == "Running - Scraping"
    
    def test_update_job_with_pdf(self, job_manager):
        """Test updating job with PDF path."""
        job_manager.add_job("https://example.com/job1")
        
        job_manager.update_job("https://example.com/job1", pdf_path="/path/to/resume.pdf")
        
        jobs = job_manager.get_all_jobs()
        assert jobs[0]["pdf_path"] == "/path/to/resume.pdf"
    
    def test_update_job_with_error(self, job_manager):
        """Test updating job with error message."""
        job_manager.add_job("https://example.com/job1")
        
        job_manager.update_job("https://example.com/job1", status="Failed", error_message="Connection timeout")
        
        jobs = job_manager.get_all_jobs()
        assert jobs[0]["status"] == "Failed"
        assert jobs[0]["error_message"] == "Connection timeout"
    
    def test_update_nonexistent_job(self, job_manager):
        """Test updating a job that doesn't exist."""
        result = job_manager.update_job("https://nonexistent.com/job", status="Running")
        assert result is False


class TestProfileManager:
    """Unit tests for ProfileManager operations."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temp directory for test data."""
        temp_dir = tempfile.mkdtemp()
        data_dir = os.path.join(temp_dir, "data")
        os.makedirs(data_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_data_dir):
        """Create a ProfileManager with patched file path."""
        import src.profile_manager as pm_module
        original = pm_module.PROFILE_FILE
        pm_module.PROFILE_FILE = os.path.join(temp_data_dir, "data", "profile.json")
        
        from src.profile_manager import ProfileManager
        manager = ProfileManager()
        yield manager
        pm_module.PROFILE_FILE = original
    
    def test_default_profile(self, profile_manager):
        """Test that default profile is created."""
        profile = profile_manager.get_profile()
        
        assert "basics" in profile
        assert "urls" in profile
        assert "demographics" in profile
        assert "work_auth" in profile
        assert "education" in profile
    
    def test_save_and_load_profile(self, profile_manager):
        """Test saving and loading profile data."""
        profile = profile_manager.get_profile()
        profile["basics"]["first_name"] = "John"
        profile["basics"]["last_name"] = "Doe"
        profile["basics"]["email"] = "john@example.com"
        
        profile_manager.save_profile(profile)
        
        loaded = profile_manager.get_profile()
        assert loaded["basics"]["first_name"] == "John"
        assert loaded["basics"]["last_name"] == "Doe"
        assert loaded["basics"]["email"] == "john@example.com"
    
    def test_profile_as_text(self, profile_manager):
        """Test converting profile to text format."""
        profile = profile_manager.get_profile()
        profile["basics"]["first_name"] = "Jane"
        profile["basics"]["last_name"] = "Smith"
        profile_manager.save_profile(profile)
        
        text = profile_manager.get_profile_as_text()
        
        assert "Jane" in text
        assert "Smith" in text
        assert "Email:" in text
        assert "LinkedIn:" in text


class TestConfigManager:
    """Unit tests for ConfigManager operations."""
    
    @pytest.fixture 
    def temp_data_dir(self):
        """Create a temp directory for test data."""
        temp_dir = tempfile.mkdtemp()
        data_dir = os.path.join(temp_dir, "data")
        os.makedirs(data_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_data_dir):
        """Create a ConfigManager with patched file path."""
        import src.config as config_module
        original_config = config_module.CONFIG_FILE
        config_module.CONFIG_FILE = os.path.join(temp_data_dir, "data", "config.json")
        
        from src.config import ConfigManager
        manager = ConfigManager()
        yield manager
        config_module.CONFIG_FILE = original_config
    
    def test_empty_feeds_initially(self, config_manager):
        """Test that feeds list is empty initially."""
        feeds = config_manager.get_feeds()
        assert feeds == []
    
    def test_add_feed(self, config_manager):
        """Test adding an RSS feed."""
        result = config_manager.add_feed("https://example.com/rss")
        assert result is True
        
        feeds = config_manager.get_feeds()
        assert len(feeds) == 1
        assert "https://example.com/rss" in feeds
    
    def test_add_duplicate_feed(self, config_manager):
        """Test that duplicate feeds are rejected."""
        config_manager.add_feed("https://example.com/rss")
        result = config_manager.add_feed("https://example.com/rss")
        assert result is False
        
        feeds = config_manager.get_feeds()
        assert len(feeds) == 1
    
    def test_remove_feed(self, config_manager):
        """Test removing an RSS feed."""
        config_manager.add_feed("https://example.com/rss")
        
        result = config_manager.remove_feed("https://example.com/rss")
        assert result is True
        
        feeds = config_manager.get_feeds()
        assert len(feeds) == 0
    
    def test_remove_nonexistent_feed(self, config_manager):
        """Test removing a feed that doesn't exist."""
        result = config_manager.remove_feed("https://nonexistent.com/rss")
        assert result is False
    
    def test_multiple_feeds(self, config_manager):
        """Test managing multiple feeds."""
        config_manager.add_feed("https://feed1.com/rss")
        config_manager.add_feed("https://feed2.com/rss")
        config_manager.add_feed("https://feed3.com/rss")
        
        feeds = config_manager.get_feeds()
        assert len(feeds) == 3
        
        config_manager.remove_feed("https://feed2.com/rss")
        
        feeds = config_manager.get_feeds()
        assert len(feeds) == 2
        assert "https://feed2.com/rss" not in feeds
