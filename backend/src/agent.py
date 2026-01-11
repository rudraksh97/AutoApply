from browser_use import Agent, Browser
from langchain_openai import ChatOpenAI
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()


class OpenRouterLLM(ChatOpenAI):
    """Wrapper for ChatOpenAI that adds browser-use compatibility."""
    provider: str = "openrouter"
    
    model_config = {"extra": "allow"}  # Allow browser-use to add attributes
    
    @property
    def model(self) -> str:
        """Return the model name for browser-use compatibility."""
        return self.model_name


class BrowserAgent:
    def __init__(self, headless=True):
        self.headless = headless
        self.llm = OpenRouterLLM(
            model="meta-llama/llama-3.3-70b-instruct:free",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        # Initialize reusable browser instance
        self.browser = Browser(headless=self.headless)

    async def scrape_job_details(self, job_link):
        """
        Opens the job link and extracts job description and requirements.
        """
        task = f"""
        Go to {job_link}.
        Extract the full job description, responsibilities, and requirements.
        Return the result as a structured string.
        """
        # Pass browser instance
        agent = Agent(task=task, llm=self.llm, browser=self.browser)
        result = await agent.run()
        return result.final_result()

    async def apply_to_job(self, job_link, resume_path, user_details):
        """
        Navigates to the job link and fills the application form.
        """
        # Ensure resume path is absolute
        abs_resume_path = os.path.abspath(resume_path)
        
        task = f"""
        Go to {job_link}.
        Find the 'Apply' button and click it to open the application form.
        Fill out the application form with the following details:
        {user_details}
        
        When asked for a resume, upload the local file found at: {abs_resume_path}
        
        If there is a submit button, click it. 
        Confirm if the application was submitted successfully.
        """
        
        # Pass browser instance
        agent = Agent(task=task, llm=self.llm, browser=self.browser)
        result = await agent.run()
        return result.final_result()

if __name__ == "__main__":
    # Test stub
    # Using venv python to test
    pass

