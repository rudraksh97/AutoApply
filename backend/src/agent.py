"""
Browser automation agent for the AutoApply application.

This module leverages the `browser-use` library and OpenRouter LLMs to
perform intelligent web scraping and form filling.

IMPORTANT: This agent NEVER submits applications. It only prepares drafts
for later manual submission by the user.
"""

import json
import os
import re

from browser_use import Agent, Browser
from browser_use.llm.openrouter.chat import ChatOpenRouter
from dotenv import load_dotenv

from src.config import ConfigManager
from src.prompts import (
    EXTRACT_FORM_TASK_TEMPLATE,
    FORM_EXTRACTION_CONTEXT,
    SCRAPE_JOB_TASK_TEMPLATE,
)

load_dotenv()


# =============================================================================
# Constants
# =============================================================================

CHROME_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--remote-debugging-port=9222",
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

REHYDRATE_DRAFT_TEMPLATE = """
You are a job application assistant. Your task is to open a saved application draft and restore the form state.

TASK: Open {job_link} and fill the form with the previously saved values.

===== SAVED FORM STATE =====
{form_state_json}

===== INSTRUCTIONS =====
1. Navigate to {job_link}
2. Wait for the form to fully load (wait for dynamic content)
3. For each field in the saved form state:
   a. Use the "xpath" field to locate the element
   b. If xpath fails, try CSS selectors based on field label or field_id
   c. Fill the field with the "value" from the saved state
   d. Handle different field types:
      - text/email/phone/textarea: Set el.value and trigger input/change events
      - select: Find matching option and set el.value
      - checkbox: Set el.checked based on value
      - radio: Find matching radio button in group and set checked
      - file: Highlight for user (browser extension handles this)
4. If a field cannot be found, note it but continue with other fields
5. DO NOT click any submit button

===== CRITICAL =====
DO NOT SUBMIT THE APPLICATION
The user will review and submit manually.

Report the results as:
{{
  "status": "rehydrated",
  "fields_restored": <number>,
  "fields_failed": <number>,
  "notes": "Any issues encountered"
}}
"""


# =============================================================================
# JSON Parsing Helpers
# =============================================================================

def _extract_json_from_response(response: str, fallback_as_text: bool = False) -> dict:
    """
    Extract JSON object from agent response.

    Args:
        response: Raw response string from agent.
        fallback_as_text: If True and no JSON found, return response as job_description.

    Returns:
        Parsed JSON dict.

    Raises:
        ValueError: If no valid JSON found and fallback disabled.
    """
    # Handle None or empty response
    if response is None:
        raise ValueError("Agent returned no result (None)")
    if not response.strip():
        raise ValueError("Agent returned empty result")

    # Strip markdown code fences if present (e.g., ```json ... ```)
    stripped = response.strip()
    if stripped.startswith("```"):
        # Remove opening fence (```json or ```)
        lines = stripped.split("\n", 1)
        if len(lines) > 1:
            stripped = lines[1]
        # Remove closing fence
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3].rstrip()
        response = stripped

    # Try direct parse first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in response
    matches = re.findall(r'(\{.*\})', response, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[-1])
        except json.JSONDecodeError:
            pass

    # Fallback for job scraping - return as raw description
    if fallback_as_text and len(response) > 100:
        return {
            "job_description": response,
            "apply_link": None,
            "company_name": None,
            "job_title": None,
            "location": None
        }

    raise ValueError(f"Failed to parse JSON from response: {response[:200]}...")


def _datetime_serializer(obj):
    """JSON serializer for datetime objects."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


# =============================================================================
# Browser Agent
# =============================================================================

class BrowserAgent:
    """
    LLM-driven browser agent for scraping and prefilling job applications.

    IMPORTANT: This agent NEVER submits applications. All automation ends
    with a filled form that the user can review and submit manually.
    """

    def __init__(self, headless: bool = True):
        """
        Initialize the browser agent.

        Args:
            headless: Whether to run the browser in headless mode.
        """
        self.headless = headless
        self.available_file_paths = []

        api_key = os.getenv("OPENROUTER_API_KEY")
        # Hardcoded model for browser-use (Gemini doesn't wrap JSON in markdown)
        model = "google/gemini-2.5-pro"
        self.llm = ChatOpenRouter(model=model, api_key=api_key)

    # -------------------------------------------------------------------------
    # Task Builders
    # -------------------------------------------------------------------------

    def _create_scrape_task(self, job_link: str) -> str:
        """Generate task string for job scraping."""
        return SCRAPE_JOB_TASK_TEMPLATE.format(job_link=job_link)

    def _create_extract_task(self, job_link: str) -> str:
        """Generate task string for form extraction."""
        return EXTRACT_FORM_TASK_TEMPLATE.format(job_link=job_link)

    def _create_rehydrate_task(self, job_link: str, form_state: dict) -> str:
        """Generate task string for draft rehydration."""
        return REHYDRATE_DRAFT_TEMPLATE.format(
            job_link=job_link,
            form_state_json=json.dumps(form_state, indent=2, default=_datetime_serializer)
        )

    # -------------------------------------------------------------------------
    # Browser Execution
    # -------------------------------------------------------------------------

    async def _run_agent(self, task: str) -> str:
        """
        Run the browser-use agent with a specific task.

        Args:
            task: Natural language instruction for the LLM agent.

        Returns:
            Final result string from the agent.
        """
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser_app = None

        try:
            # Launch browser with CDP debugging enabled
            browser_app = await playwright.chromium.launch(
                headless=self.headless,
                args=CHROME_ARGS
            )

            # Connect browser-use via CDP and execute task
            browser = Browser(cdp_url="http://localhost:9222")
            agent = Agent(
                task=task,
                llm=self.llm,
                browser=browser,
                use_vision=False,
                max_actions_per_step=5,
                max_failures=10,
                max_steps=50,
                extend_system_message=FORM_EXTRACTION_CONTEXT,
                available_file_paths=self.available_file_paths,
            )

            result = await agent.run()
            return result.final_result()

        finally:
            if browser_app:
                await browser_app.close()
            await playwright.stop()

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    async def scrape_job_details(self, job_link: str) -> dict:
        """
        Extract job description and apply link from a job posting.

        Args:
            job_link: URL of the job posting.

        Returns:
            Dict with job_description, apply_link, company_name, job_title, location.
        """
        task = self._create_scrape_task(job_link)
        result = await self._run_agent(task)

        parsed = _extract_json_from_response(result, fallback_as_text=True)

        # Validate we got useful data
        has_data = any([
            parsed.get("job_description"),
            parsed.get("apply_link"),
            parsed.get("company_name")
        ])

        if not has_data:
            raise ValueError("Parsed response contains no useful job data")

        return {
            "job_description": parsed.get("job_description", result),
            "apply_link": parsed.get("apply_link"),
            "company_name": parsed.get("company_name"),
            "job_title": parsed.get("job_title"),
            "location": parsed.get("location")
        }

    async def extract_form(self, job_link: str) -> dict:
        """
        Extract form structure from a job application page WITHOUT filling.

        Args:
            job_link: URL of the job application form.

        Returns:
            Dict with status, fields (list of field structures), total_fields, notes.

        Raises:
            ValueError: If form extraction fails or returns invalid data.
        """
        task = self._create_extract_task(job_link)
        result = await self._run_agent(task)

        parsed = _extract_json_from_response(result)

        # Validate form data
        if not parsed.get("fields") and parsed.get("status") != "no_form_found":
            raise ValueError("Extracted form contains no fields")

        return parsed

    async def open_draft(self, job_link: str, form_state: dict) -> dict:
        """
        Open a saved draft and restore form values.

        This is used for deferred completion - days or weeks after initial extraction.
        After restoration, browser automation ENDS and user takes control.

        Args:
            job_link: URL of the job posting.
            form_state: Previously saved form state with field values.

        Returns:
            Dict with status, fields_restored, fields_failed, notes.
        """
        task = self._create_rehydrate_task(job_link, form_state)
        result = await self._run_agent(task)

        return _extract_json_from_response(result)


if __name__ == "__main__":
    pass
