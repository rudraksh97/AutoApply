"""
Browser automation agent for the AutoApply application.

This module leverages the `browser-use` library and OpenRouter LLMs to 
perform intelligent web scraping and form filling. 

IMPORTANT: This agent NEVER submits applications. It only prepares drafts
for later manual submission by the user.
"""

import json
from browser_use import Agent, Browser
from browser_use.llm.openrouter.chat import ChatOpenRouter
import os
from typing import Optional

from dotenv import load_dotenv
from src.prompts import (
    SCRAPE_JOB_TASK_TEMPLATE, 
    EXTRACT_FORM_TASK_TEMPLATE,
    FORM_EXTRACTION_CONTEXT,
    # Legacy aliases
    PREFILL_JOB_TASK_TEMPLATE,
    FORM_FILLING_CONTEXT
)

load_dotenv()


# Template for reopening a draft and rehydrating the form
REHYDRATE_DRAFT_TEMPLATE = """
You are a job application assistant. Your task is to open a saved application draft and restore the form state.

TASK: Open {job_link} and fill the form with the previously saved values.

===== SAVED FORM STATE =====
{form_state_json}

===== INSTRUCTIONS =====
1. Navigate to {job_link}
2. Wait for the form to fully load
3. For each field in the saved form state, fill it with the saved value
4. If a field cannot be found, note it but continue with other fields
5. DO NOT click any submit button

===== CRITICAL =====
⚠️ DO NOT SUBMIT THE APPLICATION ⚠️
The user will review and submit manually.

Report the results as:
{{
  "status": "rehydrated",
  "fields_restored": <number of fields successfully restored>,
  "fields_failed": <number of fields that could not be restored>,
  "notes": "Any issues encountered"
}}

IMPORTANT: Return the JSON directly in your final response text. 
⚠️ DO NOT create a file, artifact, or attachment. 
⚠️ The JSON must be in the text response itself.
"""


class BrowserAgent:
    """
    An LLM-driven browser agent for scraping and prefilling job applications.

    This class maintains a reusable browser instance and provides high-level
    asynchronous methods for job-related tasks.
    
    IMPORTANT: This agent NEVER submits applications. All automation ends
    with a filled form that the user can review and submit manually.
    """
    DEFAULT_MODEL = "google/gemini-2.0-flash-001"  # Fast and reliable

    def __init__(self, headless: bool = True):
        """
        Initializes the browser agent with a specific LLM and browser config.

        Args:
            headless: Whether to run the browser in headless mode.
        """
        self.headless = headless
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            # We don't raise here to allow instantiation, but it might fail later.
            # Ideally logs a warning.
            pass
            
        self.llm = ChatOpenRouter(
            model=self.DEFAULT_MODEL,
            api_key=api_key,
        )
        # Initialize reusable browser instance
        self.browser = Browser(headless=self.headless)
        # File paths available for upload (set per-task)
        self.available_file_paths = []

    def _create_scrape_task(self, job_link: str) -> str:
        """Generates the LLM task string for job scraping."""
        return SCRAPE_JOB_TASK_TEMPLATE.format(job_link=job_link)

    def _create_extract_task(self, job_link: str) -> str:
        """Generates the LLM task string for form extraction (no filling)."""
        return EXTRACT_FORM_TASK_TEMPLATE.format(job_link=job_link)

    def _create_prefill_task(self, job_link: str, resume_path: str, user_details: str) -> str:
        """DEPRECATED: Use _create_extract_task instead."""
        # Now just extracts, doesn't fill
        return self._create_extract_task(job_link)

    def _create_rehydrate_task(self, job_link: str, form_state: dict) -> str:
        """Generates the LLM task string for reopening a saved draft."""
        # Handle datetime serialization
        def json_serializer(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            raise TypeError(f'Object of type {type(obj)} is not JSON serializable')
        
        return REHYDRATE_DRAFT_TEMPLATE.format(
            job_link=job_link,
            form_state_json=json.dumps(form_state, indent=2, default=json_serializer)
        )

    async def _run_agent(self, task: str) -> str:
        """
        Helper to run the browser-use agent with a specific task string.

        Args:
            task: The natural language instruction for the LLM agent.

        Returns:
            The final result/string reported by the agent.

        Raises:
            Exception: If the browser-use internal logic or LLM call fails.
        """
        # Create a fresh browser instance for each task to avoid CDP issues
        # The browser-use library doesn't handle browser reuse well after session cleanup
        browser = Browser(headless=self.headless)
        
        try:
            # Pass browser instance with enhanced configuration
            agent = Agent(
                task=task,
                llm=self.llm,
                browser=browser,
                use_vision=False,  # DOM-only mode more reliable for form filling
                max_actions_per_step=5,  # Allow more actions per reasoning step
                max_failures=10,  # Keep trying on errors - don't give up easily
                max_steps=50,  # Allow more steps to complete complex forms
                extend_system_message=FORM_EXTRACTION_CONTEXT,  # Inject form extraction guidance
                available_file_paths=self.available_file_paths,  # Allow file uploads
            )
            result = await agent.run()
            return result.final_result()
        except Exception as e:
            # Re-raise to be handled by the caller (service layer)
            raise e

    async def scrape_job_details(self, job_link: str) -> str:
        """
        Opens a job link and extracts the full description.

        Args:
            job_link: The URL of the job posting.

        Returns:
            Extracted text describing the job.
        """
        task = self._create_scrape_task(job_link)
        return await self._run_agent(task)

    async def extract_form(self, job_link: str) -> dict:
        """
        Opens a job application form and extracts its structure WITHOUT filling.
        
        This is the primary method for the new extraction-first workflow.
        The agent only discovers form fields and extracts labels/xpaths.
        A separate LLM step will generate the answers.

        Args:
            job_link: The URL of the job posting.

        Returns:
            A dict containing:
            - status: "extracted" on success
            - fields: List of field structures with xpath, label, field_type, options
            - total_fields: Number of fields found
            - notes: Any observations about the form
            
        Raises:
            Exception: If form extraction fails
            json.JSONDecodeError: If agent returns malformed JSON
        """
        task = self._create_extract_task(job_link)
        result = await self._run_agent(task)
        
        # Parse the JSON result from the agent
        import re
        try:
            # Try direct parse first
            return json.loads(result)
        except json.JSONDecodeError:
            # Try regex extraction
            match = re.search(r"(\{.*\})", result, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # If all parsing fails, return fallback
            return {
                "status": "extracted",
                "fields": [],
                "total_fields": 0,
                "notes": result,
                "raw_response": True
            }

    async def prefill_form(self, job_link: str, resume_path: str, user_details: str) -> dict:
        """
        DEPRECATED: Use extract_form instead.
        
        This method now just calls extract_form for backwards compatibility.
        The filling is now done by the extension using LLM-generated values.
        """
        return await self.extract_form(job_link)

    async def open_draft(self, job_link: str, form_state: dict) -> dict:
        """
        Opens a saved draft in the browser and rehydrates the form.
        
        This is a deferred action that can happen hours, days, or weeks after
        the original draft was created. It opens the job URL and attempts to
        restore all saved field values.
        
        After rehydration, browser automation ENDS. The user takes manual
        control to review and submit.

        Args:
            job_link: The URL of the job posting.
            form_state: Previously saved form state with field values.

        Returns:
            A dict containing:
            - status: "rehydrated" on success
            - fields_restored: Number of fields successfully restored
            - fields_failed: Number of fields that couldn't be restored
            - notes: Any issues encountered
        """
        task = self._create_rehydrate_task(job_link, form_state)
        result = await self._run_agent(task)
        
        # Parse the JSON result from the agent
        import re
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Try regex extraction
            match = re.search(r"(\{.*\})", result, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            
            return {
                "status": "rehydrated",
                "fields_restored": 0,
                "fields_failed": 0,
                "notes": result,
                "raw_response": True
            }

    # Legacy method alias for backwards compatibility during migration
    async def apply_to_job(self, job_link: str, resume_path: str, user_details: str) -> str:
        """
        DEPRECATED: Use prefill_form instead.
        
        This method now calls prefill_form and returns a string result
        for backwards compatibility with existing callers.
        """
        result = await self.prefill_form(job_link, resume_path, user_details)
        return json.dumps(result)


if __name__ == "__main__":
    # Test stub
    pass

