"""
Shared pytest fixtures for E2E integration tests.

These fixtures support testing the real AutoApply workflow with:
- Isolated temporary directories per test
- Real JobManager and ResumeBuilder instances
- Stubbed BrowserAgent for apply operations (but real for scraping simulation)
"""
import pytest
import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Ensure backend imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Session-scoped fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests (session-scoped for efficiency)."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def fixtures_dir():
    """Path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def job_posting_html(fixtures_dir):
    """Contents of the test job posting HTML file."""
    with open(fixtures_dir / "job_posting.html", "r") as f:
        return f.read()


@pytest.fixture(scope="session")
def valid_template_path(fixtures_dir):
    """Path to the valid LaTeX template."""
    return str(fixtures_dir / "valid_template.tex")


@pytest.fixture(scope="session")
def invalid_template_path(fixtures_dir):
    """Path to the invalid LaTeX template (missing skills_list)."""
    return str(fixtures_dir / "invalid_template.tex")


# ============================================================================
# Function-scoped fixtures (isolated per test)
# ============================================================================

@pytest.fixture
def temp_data_dir():
    """
    Create an isolated temporary directory for test data.
    
    This directory contains:
    - data/ subdirectory for jobs.json, resumes, etc.
    - Cleaned up after each test
    """
    temp_dir = tempfile.mkdtemp(prefix="autoapply_e2e_")
    data_dir = os.path.join(temp_dir, "data")
    os.makedirs(data_dir)
    
    # Create generated_resumes subdirectory
    resumes_dir = os.path.join(data_dir, "generated_resumes")
    os.makedirs(resumes_dir)
    
    # Store original working directory
    original_cwd = os.getcwd()
    
    yield temp_dir
    
    # Cleanup
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_job_manager(temp_data_dir, monkeypatch):
    """
    Create a JobManager instance using the temporary data directory.
    
    Uses monkeypatch to redirect the JOBS_FILE constant.
    """
    from src.job_manager import JobManager
    
    jobs_file = os.path.join(temp_data_dir, "data", "jobs.json")
    monkeypatch.setattr("src.job_manager.JOBS_FILE", jobs_file)
    
    # Also patch the data directory check
    data_dir = os.path.join(temp_data_dir, "data")
    
    class TempJobManager(JobManager):
        def _ensure_file(self):
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            if not os.path.exists(jobs_file):
                import json
                with open(jobs_file, 'w') as f:
                    json.dump([], f)
    
    return TempJobManager()


@pytest.fixture
def temp_resume_builder(temp_data_dir, valid_template_path):
    """
    Create a ResumeBuilder instance using the temporary directory and valid template.
    """
    from src.resume_builder import ResumeBuilder
    
    # Copy the valid template to the temp data dir
    template_dest = os.path.join(temp_data_dir, "data", "resume_base.tex")
    shutil.copy(valid_template_path, template_dest)
    
    output_dir = os.path.join(temp_data_dir, "data", "generated_resumes")
    
    return ResumeBuilder(
        base_template_path=template_dest,
        output_dir=output_dir
    )


@pytest.fixture
def invalid_resume_builder(temp_data_dir, invalid_template_path):
    """
    Create a ResumeBuilder instance with an invalid template (missing skills_list).
    """
    from src.resume_builder import ResumeBuilder
    
    # Copy the invalid template to the temp data dir
    template_dest = os.path.join(temp_data_dir, "data", "invalid_template.tex")
    shutil.copy(invalid_template_path, template_dest)
    
    output_dir = os.path.join(temp_data_dir, "data", "generated_resumes")
    
    return ResumeBuilder(
        base_template_path=template_dest,
        output_dir=output_dir
    )


@pytest.fixture
def stub_browser_agent(job_posting_html):
    """
    Create a stubbed BrowserAgent that:
    - Returns the fixture HTML for scraping (simulates reading a job page)
    - Returns success for apply_to_job (avoids touching real job boards)
    
    This is the ONLY stubbed component in E2E tests.
    The scraping "result" is actually the parsed job description content from the fixture.
    """
    agent = Mock()
    
    # For scrape_job_details: return a realistic job description parsed from fixture
    job_description = """
    Senior Software Engineer - Test Company Inc.
    Location: San Francisco, CA (Remote)
    
    About the Role:
    We are looking for a Senior Software Engineer to join our team and help build
    scalable distributed systems.
    
    Responsibilities:
    - Design and implement scalable backend services using Python and Go
    - Build and maintain CI/CD pipelines
    - Mentor junior engineers and conduct code reviews
    - Participate in on-call rotations
    
    Requirements:
    - 5+ years of software engineering experience
    - Strong proficiency in Python, with experience in Django or FastAPI
    - Experience with AWS (EC2, S3, Lambda, RDS)
    - Familiarity with Docker and Kubernetes
    - Experience with PostgreSQL and Redis
    - Strong understanding of REST APIs and microservices architecture
    - Experience with Git and GitHub workflows
    
    Nice to Have:
    - Experience with React or TypeScript
    - Familiarity with Terraform or infrastructure as code
    - Experience with GraphQL
    """
    agent.scrape_job_details = AsyncMock(return_value=job_description)
    
    # For apply_to_job: simulate successful submission
    agent.apply_to_job = AsyncMock(return_value="Application submitted successfully")
    
    return agent


@pytest.fixture
def failing_browser_agent():
    """
    Create a stubbed BrowserAgent that fails during scraping.
    Used for testing error propagation.
    """
    agent = Mock()
    agent.scrape_job_details = AsyncMock(
        side_effect=Exception("Network timeout: Failed to load job page")
    )
    agent.apply_to_job = AsyncMock(return_value="N/A")
    return agent


# ============================================================================
# Prerequisite check fixtures
# ============================================================================

@pytest.fixture(scope="session")
def check_openrouter_api_key():
    """
    Check that OPENROUTER_API_KEY is set.
    
    Returns the key if available, otherwise None.
    This fixture does NOT skip tests - that's handled by the test module.
    """
    return os.environ.get("OPENROUTER_API_KEY")


@pytest.fixture(scope="session")
def check_pdflatex():
    """
    Check that pdflatex is available in PATH.
    
    Returns True if available, False otherwise.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["pdflatex", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture
def e2e_prerequisites(check_openrouter_api_key, check_pdflatex):
    """
    Combined prerequisite check for E2E tests.
    
    Returns a dict with status of each prerequisite.
    Tests should skip if any prerequisite is missing.
    """
    return {
        "api_key_present": bool(check_openrouter_api_key),
        "pdflatex_available": check_pdflatex,
        "all_met": bool(check_openrouter_api_key) and check_pdflatex
    }


# ============================================================================
# Browser Agent Test Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def job_application_page_path(fixtures_dir):
    """Path to the fake job application HTML page."""
    return fixtures_dir / "job_application_page.html"


@pytest.fixture(scope="function")
def local_test_server(fixtures_dir):
    """
    Start a local HTTP server to serve test fixture files.
    
    This allows the browser agent to access test pages via HTTP
    instead of file:// protocol, which is more realistic.
    
    Yields the base URL (e.g., 'http://localhost:8765')
    """
    import http.server
    import socketserver
    import threading
    
    PORT = 8765
    
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        """HTTP handler that doesn't log to console."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(fixtures_dir), **kwargs)
        
        def log_message(self, format, *args):
            pass  # Suppress logging
    
    # Try to find an available port
    for port in range(PORT, PORT + 10):
        try:
            httpd = socketserver.TCPServer(("", port), QuietHandler)
            break
        except OSError:
            continue
    else:
        pytest.skip("Could not find an available port for test server")
    
    # Start server in background thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    yield f"http://localhost:{port}"
    
    # Cleanup
    httpd.shutdown()


@pytest.fixture
def real_browser_agent():
    """
    Create a REAL BrowserAgent instance for browser automation tests.
    
    This is NOT stubbed - it actually controls a browser.
    Requires playwright to be installed.
    """
    from src.agent import BrowserAgent
    return BrowserAgent(headless=True)


@pytest.fixture
def test_user_profile():
    """
    Test user profile data for filling out job applications.
    """
    return {
        "full_name": "Test User",
        "email": "testuser@example.com",
        "phone": "(555) 123-4567",
        "linkedin": "https://linkedin.com/in/testuser",
        "portfolio": "https://testuser.dev",
        "experience": "5-10 years",
        "cover_letter": "I am excited to apply for this position. I have 7 years of experience in software engineering.",
        "salary": "$150,000 - $180,000",
        "start_date": "2 weeks notice"
    }


@pytest.fixture
def test_user_profile_text(test_user_profile):
    """
    Test user profile formatted as text for the browser agent.
    """
    return f"""
Full Name: {test_user_profile['full_name']}
Email: {test_user_profile['email']}
Phone: {test_user_profile['phone']}
LinkedIn: {test_user_profile['linkedin']}
Portfolio: {test_user_profile['portfolio']}
Years of Experience: {test_user_profile['experience']}
Cover Letter: {test_user_profile['cover_letter']}
Expected Salary: {test_user_profile['salary']}
Start Date: {test_user_profile['start_date']}
Work Authorization: Yes, I am authorized to work in the United States
"""

