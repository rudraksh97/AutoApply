"""End-to-End Integration Tests for AutoApply Workflow.

This module contains integration tests that verify the full "pending to completed"
workflow using real system components where possible.

Key Features Tested:
    * Real LLM API calls via OpenRouter for keyword extraction.
    * Real LaTeX compilation using pdflatex to produce actual PDF files.
    * Real JobManager JSON persistence (reads and writes to jobs.json).
    * Real job lifecycle state transitions.
    * Real ResumeBuilder template rendering with Jinja2.

Design Decisions:
    Mocking is intentionally minimized to catch integration failures such as:
    * LLM response format changes.
    * LaTeX template syntax errors.
    * File system permission issues.
    * State persistence race conditions.

    Only `BrowserAgent.apply_to_job` is stubbed to prevent destructive actions
    on external websites.

Usage:
    These tests are opt-in and require:
    1. Environment variable: RUN_E2E_LLM_TESTS=1
    2. OPENROUTER_API_KEY set in environment
    3. pdflatex installed and in PATH
"""
import pytest
import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Skip Configuration
# ============================================================================

# Check if E2E tests should run
E2E_ENABLED = os.environ.get("RUN_E2E_LLM_TESTS", "0") == "1"

skip_unless_e2e = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="E2E tests disabled. Set RUN_E2E_LLM_TESTS=1 to enable."
)


# ============================================================================
# Test Helpers
# ============================================================================

async def run_with_retry(coro_func, *args, max_retries=2, timeout=90, retry_delay=5, **kwargs):
    """Executes an async function with timeout and retry logic.

    Args:
        coro_func: The async function to execute.
        *args: Positional arguments for the function.
        max_retries: Maximum number of retry attempts (default: 2).
        timeout: Timeout in seconds for each attempt (default: 90).
        retry_delay: Delay in seconds between retries (default: 5).
        **kwargs: Keyword arguments for the function.

    Returns:
        The result of the coroutine function.

    Raises:
        asyncio.TimeoutError: If the operation times out after all retries.
        Exception: If the operation fails with a non-retryable error or after retries.
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(coro_func(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            last_exception = asyncio.TimeoutError(f"Operation timed out after {timeout}s")
            if attempt < max_retries:
                print(f"Attempt {attempt + 1} timed out, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
        except Exception as e:
            last_exception = e
            if attempt < max_retries and "rate limit" in str(e).lower():
                print(f"Attempt {attempt + 1} hit rate limit, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                raise
    
    if last_exception:
        raise last_exception


# ============================================================================
# Test Constants
# ============================================================================

TEST_JOB_URL = "https://example.com/jobs/senior-software-engineer-12345"
TEST_RESUME_INFO = """
Software Engineer with 5 years of experience in Python, AWS, and Web Development.
Education: BS in Computer Science.
Key Skills: Python, Django, React, Docker, Kubernetes.
"""


# ============================================================================
# Test Class: Happy Path
# ============================================================================

@skip_unless_e2e
class TestHappyPathFullWorkflow:
    """Tests the complete AutoApply workflow end-to-end.

    This test suite exercises:
        * Real LLM API calls for keyword extraction
        * Real LaTeX compilation to PDF
        * Real JobManager state persistence
        * All job status transitions

    Note:
        Only BrowserAgent is stubbed to avoid touching external job boards.
    """
    
    @pytest.fixture(autouse=True)
    def setup(self, e2e_prerequisites):
        """Skip if prerequisites not met."""
        if not e2e_prerequisites["all_met"]:
            pytest.skip("E2E prerequisites (API key, pdflatex) not met.")
    
    @pytest.mark.asyncio
    async def test_full_workflow_pending_to_completed(
        self, 
        temp_data_dir, 
        temp_job_manager, 
        temp_resume_builder,
        stub_browser_agent
    ):
        """Verifies the complete job application workflow from Pending to Completed.

        Steps Verified:
            1. Job starts in Pending state.
            2. Transitions through all Running states (Scraping, Generating, Applying).
            3. LLM returns valid skills_list.
            4. Real PDF is generated.
            5. Final status is Completed.
        """
        from src.services import JobApplicationService
        
        # Track status transitions
        status_history = []
        
        # Set up job manager to track updates
        original_update = temp_job_manager.update_job
        def tracking_update(url, status=None, **kwargs):
            if status:
                status_history.append(status)
            return original_update(url, status=status, **kwargs)
        temp_job_manager.update_job = tracking_update
        
        # Add the job as Pending
        temp_job_manager.add_job(TEST_JOB_URL, status="Pending")
        
        # Verify initial state
        jobs = temp_job_manager.get_all_jobs()
        assert len(jobs) == 1
        assert jobs[0]["status"] == "Pending"
        
        log_messages = []
        
        service = JobApplicationService(
            job_manager=temp_job_manager,
            browser_agent=stub_browser_agent,
            resume_builder=temp_resume_builder
        )
        
        result = await run_with_retry(
            service.process_job,
            job_link=TEST_JOB_URL,
            user_details_text="Test User\ntest@example.com",
            log_callback=lambda msg: log_messages.append(msg)
        )
        
        # Verify workflow succeeded
        assert result is True, f"Workflow should return True. Log: {log_messages}"
        
        # Verify status transitions occurred in correct order
        expected_statuses = [
            "Running - Scraping",
            "Running - Generating Resume",
            "Running - Resume Ready",
            "Running - Applying",
            "Completed"
        ]
        
        for expected in expected_statuses:
            assert expected in status_history, \
                f"Missing status '{expected}' in transitions: {status_history}"
        
        # Verify Completed came after all Running states
        completed_idx = status_history.index("Completed")
        for running_status in ["Running - Scraping", "Running - Generating Resume"]:
            assert status_history.index(running_status) < completed_idx, \
                f"{running_status} should come before Completed"
        
        # Verify PDF was created
        jobs = temp_job_manager.get_all_jobs()
        final_job = next(j for j in jobs if j["url"] == TEST_JOB_URL)
        
        assert final_job["status"] == "Completed"
        assert final_job["pdf_path"] is not None
        assert os.path.exists(final_job["pdf_path"]), \
            f"PDF should exist at {final_job['pdf_path']}"
        
        # Verify it's a real PDF (check magic bytes)
        with open(final_job["pdf_path"], "rb") as f:
            magic = f.read(4)
            assert magic == b"%PDF", "Generated file should be a valid PDF"
        
        print(f"\n✅ Happy path test passed!")
        print(f"   Status transitions: {' → '.join(status_history)}")
        print(f"   PDF generated: {final_job['pdf_path']}")
    
    @pytest.mark.asyncio
    async def test_llm_extracts_valid_skills(self, temp_resume_builder):
        """Verifies that the LLM returns a valid skills_list from a job description."""
        job_description = "Senior Software Engineer. Requirements: Python, AWS, Docker, Kubernetes, PostgreSQL."
        
        result = await run_with_retry(
            asyncio.get_event_loop().run_in_executor,
            None,
            temp_resume_builder.generate_resume_content,
            job_description,
            TEST_RESUME_INFO
        )
        
        assert "skills_list" in result
        skills = result["skills_list"]
        assert isinstance(skills, list) and len(skills) > 0
        
        # Verify relevance
        skills_lower = [s.lower() for s in skills]
        expected = ["python", "aws", "docker"]
        assert sum(1 for kw in expected if any(kw in s for s in skills_lower)) >= 1



# ============================================================================
# Failure & Edge Case Tests
# ============================================================================

@skip_unless_e2e
class TestWorkflowRobustness:
    """Tests failure propagation, edge cases, and cleanup logic."""

    @pytest.fixture(autouse=True)
    def setup(self, e2e_prerequisites):
        if not e2e_prerequisites["all_met"]:
            pytest.skip("E2E prerequisites not met.")

    @pytest.mark.asyncio
    async def test_malformed_llm_response_causes_failure(self, temp_data_dir, temp_job_manager, stub_browser_agent):
        """Verifies graceful failure when the LLM returns a malformed response."""
        from src.services import JobApplicationService
        from src.resume_builder import ResumeBuilder

        class FailingResumeBuilder(ResumeBuilder):
            def generate_resume_content(self, *args): return {"invalid": "data"}

        output_dir = Path(temp_data_dir) / "data" / "re"
        output_dir.mkdir(parents=True, exist_ok=True)
        template_path = Path(temp_data_dir) / "data" / "resume_base.tex"
        template_path.write_text(r"\documentclass{article}\begin{document}\VAR{skills_list}\end{document}")

        builder = FailingResumeBuilder(base_template_path=str(template_path), output_dir=str(output_dir))
        temp_job_manager.add_job(TEST_JOB_URL, status="Pending")
        service = JobApplicationService(temp_job_manager, stub_browser_agent, builder)

        assert await service.process_job(TEST_JOB_URL, "Test User") is False
        assert temp_job_manager.get_all_jobs()[0]["status"] == "Failed"
        assert len(list(output_dir.glob("*.pdf"))) == 0

    @pytest.mark.asyncio
    async def test_invalid_latex_template_causes_failure(self, temp_data_dir, temp_job_manager, stub_browser_agent):
        """Verifies failure handling when the LaTeX template is invalid."""
        from src.services import JobApplicationService
        from src.resume_builder import ResumeBuilder

        template_path = Path(temp_data_dir) / "data" / "broken.tex"
        template_path.write_text(r"\documentclass{article}\begin{document}\undefined\end{document}")
        output_dir = Path(temp_data_dir) / "data" / "re"
        output_dir.mkdir(parents=True, exist_ok=True)

        builder = ResumeBuilder(base_template_path=str(template_path), output_dir=str(output_dir))
        temp_job_manager.add_job(TEST_JOB_URL, status="Pending")
        service = JobApplicationService(temp_job_manager, stub_browser_agent, builder)

        assert await service.process_job(TEST_JOB_URL, "Test User") is False
        job = temp_job_manager.get_all_jobs()[0]
        assert job["status"] == "Failed"
        assert "latex" in job["error_message"].lower()

    @pytest.mark.asyncio
    async def test_job_persistence(self, temp_data_dir, monkeypatch):
        """Verifies that job state is correctly persisted across JobManager instances."""
        from src.job_manager import JobManager
        jobs_file = os.path.join(temp_data_dir, "data", "jobs.json")
        os.makedirs(os.path.dirname(jobs_file), exist_ok=True)
        with open(jobs_file, 'w') as f: json.dump([], f)
        monkeypatch.setattr("src.job_manager.JOBS_FILE", jobs_file)

        m1 = JobManager()
        m1.add_job(TEST_JOB_URL, status="Pending")
        m2 = JobManager()
        assert m2.get_all_jobs()[0]["url"] == TEST_JOB_URL

    @pytest.mark.asyncio
    async def test_aux_files_cleaned(self, temp_resume_builder):
        """Verifies that LaTeX auxiliary files (.aux, .log, .out) are cleaned up."""
        ctx = {"summary":"s", "experience":"e", "education":"d", "skills_list":["p"]}
        tex = temp_resume_builder.render_tex(ctx, "test")
        pdf = temp_resume_builder.compile_pdf(tex)
        assert os.path.exists(pdf)
        base = tex.replace('.tex', '')
        for ext in ['.aux', '.log', '.out']:
            assert not os.path.exists(base + ext)



# ============================================================================
# Real Browser Agent Tests
# ============================================================================

@skip_unless_e2e
class TestRealBrowserAgent:
    """Tests browser automation (scrapes & fills) using real LLMs/Parsers."""

    @pytest.fixture(autouse=True)
    def setup(self, check_openrouter_api_key):
        if not check_openrouter_api_key:
            pytest.skip("OPENROUTER_API_KEY not set.")

    @pytest.mark.asyncio
    async def test_browser_agent_fills_form(self, local_test_server, real_browser_agent, test_user_profile_text, temp_data_dir):
        """Verifies that the browser agent can correctly fill a locally-served job application form."""
        resume_path = os.path.join(temp_data_dir, "test.pdf")
        with open(resume_path, 'wb') as f: f.write(b'%PDF-1.4\n%Fake\n')
        
        url = f"{local_test_server}/job_application_page.html"
        await asyncio.sleep(5)  # Brief wait

        result = await run_with_retry(
            real_browser_agent.apply_to_job,
            job_link=url, resume_path=resume_path, user_details=test_user_profile_text,
            timeout=180
        )
        assert result is not None
        assert any(ind in result.lower() for ind in ["submitted", "success", "completed"])

    @pytest.mark.asyncio
    async def test_browser_agent_scrapes_page(self, local_test_server, real_browser_agent):
        """Verifies that the browser agent can scrape content from a locally-served job posting."""
        url = f"{local_test_server}/job_posting.html"
        await asyncio.sleep(5)

        result = await run_with_retry(real_browser_agent.scrape_job_details, url, timeout=120)
        assert result and len(result) > 50
        assert any(term in result.lower() for term in ["python", "aws", "docker"])
        
        assert result is not None, "Scraping should return content"
        assert len(result) > 50, f"Should scrape substantial content, got {len(result)} chars"
        
        # Verify some expected content from the job posting was extracted
        result_lower = result.lower()
        expected_terms = ["software engineer", "python", "aws", "docker"]
        matches = sum(1 for term in expected_terms if term in result_lower)
        
        print(f"\n📄 Scraped {len(result)} characters")
        print(f"   Matched {matches}/{len(expected_terms)} expected terms")
        print(f"   Preview: {result[:300]}...")
        
        assert matches >= 2, \
            f"Expected at least 2 matching terms. Found {matches}. Content: {result[:500]}"
        
        print(f"\n✅ Browser agent scraping test passed")


if __name__ == "__main__":
    # Allow running directly with python for debugging
    pytest.main([__file__, "-v", "-s"])

