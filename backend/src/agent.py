"""
Browser automation agent for the AutoApply application.

This module leverages the `browser-use` library and OpenRouter LLMs to 
perform intelligent web scraping and form filling. It can handle complex
interative elements by describing the intent to the LLM.
"""

from browser_use import Agent, Browser
from browser_use.llm.openrouter.chat import ChatOpenRouter
import os

from dotenv import load_dotenv

load_dotenv()


class BrowserAgent:
    """
    An LLM-driven browser agent for scraping and applying to jobs.

    This class maintains a reusable browser instance and provides high-level
    asynchronous methods for job-related tasks.
    """
    DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

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

    def _create_scrape_task(self, job_link: str) -> str:
        """Generates the LLM task string for job scraping."""
        return f"""
        Go to {job_link}.
        Extract the full job description, responsibilities, and requirements.
        Return the result as a structured string.
        """

    def _create_apply_task(self, job_link: str, resume_path: str, user_details: str) -> str:
        """Generates the LLM task string for job application submission."""
        # Ensure resume path is absolute
        abs_resume_path = os.path.abspath(resume_path)
        return f"""
        Go to {job_link}.
        Find the 'Apply' button and click it to open the application form.
        Fill out the application form with the following details:
        {user_details}
        
        When asked for a resume, upload the local file found at: {abs_resume_path}
        
        If there is a submit button, click it. 
        Confirm if the application was submitted successfully.
        """

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
        try:
            # Pass browser instance
            agent = Agent(
                task=task,
                llm=self.llm,
                browser=self.browser,
                use_vision=False,
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

    async def apply_to_job(self, job_link: str, resume_path: str, user_details: str) -> str:
        """
        Submits an application to the specified job URL.

        Args:
            job_link: The URL of the job posting.
            resume_path: Path to the tailored resume PDF.
            user_details: Text info used to fill form fields.

        Returns:
            The outcome message from the agent.
        """
        task = self._create_apply_task(job_link, resume_path, user_details)
        return await self._run_agent(task)

if __name__ == "__main__":
    # Test stub
    pass

