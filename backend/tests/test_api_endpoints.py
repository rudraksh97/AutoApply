"""
API endpoint tests using FastAPI TestClient.

Tests all REST endpoints without starting a real server.
"""
import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient


class TestAPIEndpoints:
    """Tests for FastAPI endpoints."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create temp data directory for test isolation."""
        temp_dir = tempfile.mkdtemp()
        data_dir = os.path.join(temp_dir, "data")
        os.makedirs(data_dir)
        
        # Create necessary files
        with open(os.path.join(data_dir, "jobs.json"), 'w') as f:
            json.dump([], f)
        with open(os.path.join(data_dir, "config.json"), 'w') as f:
            json.dump({"rss_feeds": []}, f)
        with open(os.path.join(data_dir, "profile.json"), 'w') as f:
            json.dump({
                "basics": {"first_name": "Test", "last_name": "User", "email": "test@example.com", "phone": "", "location": ""},
                "urls": {"linkedin": "", "github": "", "portfolio": ""},
                "demographics": {"gender": "Prefer not to say", "nationality": "", "veteran": "", "disability": ""},
                "work_auth": {"authorized_in_us": True, "requires_sponsorship": False},
                "education": {"degree": "", "university": "", "field_of_study": "", "graduation_year": ""}
            }, f)
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def client(self, temp_data_dir):
        """Create test client with patched paths."""
        # Patch all file paths before importing
        import src.job_manager as jm
        import src.config as cfg
        import src.profile_manager as pm
        
        orig_jobs = jm.JOBS_FILE
        orig_config = cfg.CONFIG_FILE
        orig_profile = pm.PROFILE_FILE
        
        jm.JOBS_FILE = os.path.join(temp_data_dir, "data", "jobs.json")
        cfg.CONFIG_FILE = os.path.join(temp_data_dir, "data", "config.json")
        pm.PROFILE_FILE = os.path.join(temp_data_dir, "data", "profile.json")
        
        # Patch the static files directory
        with patch.dict(os.environ, {"DATA_DIR": os.path.join(temp_data_dir, "data")}):
            from api.server import app
            client = TestClient(app)
            yield client
        
        jm.JOBS_FILE = orig_jobs
        cfg.CONFIG_FILE = orig_config
        pm.PROFILE_FILE = orig_profile


class TestJobsEndpoints(TestAPIEndpoints):
    """Tests for /jobs endpoints."""
    
    def test_get_jobs_empty(self, client):
        """Test getting jobs when list is empty."""
        response = client.get("/jobs/")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_retry_nonexistent_job(self, client):
        """Test retrying a job that doesn't exist."""
        response = client.post("/jobs/retry", json={"url": "https://example.com/job"})
        # Should handle gracefully - 404 when job not found
        assert response.status_code in [200, 404]


class TestFeedsEndpoints(TestAPIEndpoints):
    """Tests for /feeds endpoints."""
    
    def test_get_feeds_empty(self, client):
        """Test getting feeds when list is empty."""
        response = client.get("/feeds/")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_add_feed(self, client):
        """Test adding a new RSS feed."""
        response = client.post("/feeds/", json={"url": "https://example.com/rss"})
        assert response.status_code == 200
        
        response = client.get("/feeds/")
        assert "https://example.com/rss" in response.json()
    
    def test_delete_feed(self, client):
        """Test removing an RSS feed."""
        # Add first
        client.post("/feeds/", json={"url": "https://example.com/rss"})
        
        # Delete - use request() for DELETE with body
        response = client.request("DELETE", "/feeds/", json={"url": "https://example.com/rss"})
        assert response.status_code == 200
        
        response = client.get("/feeds/")
        assert "https://example.com/rss" not in response.json()


class TestProfileEndpoints(TestAPIEndpoints):
    """Tests for /profile endpoints."""
    
    def test_get_profile(self, client):
        """Test getting user profile."""
        response = client.get("/profile/")
        assert response.status_code == 200
        
        data = response.json()
        assert "basics" in data
        assert data["basics"]["first_name"] == "Test"
    
    def test_update_profile(self, client):
        """Test updating user profile."""
        new_profile = {
            "basics": {"first_name": "Updated", "last_name": "Name", "email": "new@example.com", "phone": "555-1234", "location": "NYC"},
            "urls": {"linkedin": "https://linkedin.com/in/test", "github": "https://github.com/test", "portfolio": ""},
            "demographics": {"gender": "Prefer not to say", "nationality": "US", "veteran": "No", "disability": "No"},
            "work_auth": {"authorized_in_us": True, "requires_sponsorship": False},
            "education": {"degree": "BS", "university": "MIT", "field_of_study": "CS", "graduation_year": "2020"}
        }
        
        # Use POST not PUT since router defines POST
        response = client.post("/profile/", json=new_profile)
        assert response.status_code == 200
        
        response = client.get("/profile/")
        data = response.json()
        assert data["basics"]["first_name"] == "Updated"
        assert data["education"]["university"] == "MIT"


class TestUploadTemplate(TestAPIEndpoints):
    """Tests for /upload-template endpoint."""
    
    def test_upload_valid_template(self, client, temp_data_dir):
        """Test uploading a valid LaTeX template."""
        # Create a valid template with required placeholder
        template_content = b"""
        \\documentclass{article}
        \\begin{document}
        Skills: \\VAR{skills_list}
        \\end{document}
        """
        
        response = client.post(
            "/upload-template",
            files={"file": ("resume.tex", template_content, "application/x-tex")}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "uploaded"
    
    def test_upload_invalid_extension(self, client):
        """Test uploading a non-.tex file."""
        response = client.post(
            "/upload-template",
            files={"file": ("resume.pdf", b"PDF content", "application/pdf")}
        )
        
        assert response.status_code == 400
        assert "Only .tex files" in response.json()["detail"]
    
    def test_upload_missing_placeholder(self, client):
        """Test uploading template without required placeholder."""
        template_content = b"""
        \\documentclass{article}
        \\begin{document}
        No skills placeholder here
        \\end{document}
        """
        
        response = client.post(
            "/upload-template",
            files={"file": ("resume.tex", template_content, "application/x-tex")}
        )
        
        assert response.status_code == 400
        assert "skills_list" in response.json()["detail"]


class TestControlEndpoints(TestAPIEndpoints):
    """Tests for /start and /stop control endpoints."""
    
    @patch('api.server.run_auto_apply', new_callable=AsyncMock)
    def test_start_automation(self, mock_run, client):
        """Test starting automation."""
        response = client.post("/start")
        assert response.status_code == 200
        assert response.json()["status"] in ["started", "already_running"]
    
    def test_stop_automation_when_not_running(self, client):
        """Test stopping automation when not running."""
        # Reset state
        from api.server import service_state
        service_state.is_running = False
        
        response = client.post("/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "not_running"
