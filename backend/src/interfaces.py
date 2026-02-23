"""
This module defines the core interfaces (Protocols) for the AutoApply application.

Following the Dependency Inversion Principle, these protocols allow the service layer
to depend on abstractions rather than concrete implementations, facilitating
testability and modularity.
"""

from typing import Protocol, List, Any, Optional

class JobManagerProtocol(Protocol):
    """
    Protocol defining the requirements for persistent job management.
    """
    def update_job(
        self, 
        url: str, 
        status: Optional[str] = None, 
        pdf_path: Optional[str] = None, 
        details: Optional[str] = None, 
        error_message: Optional[str] = None
    ) -> bool:
        """
        Updates the status and metadata of a specific job.

        Args:
            url: The unique URL of the job.
            status: The current processing status (e.g., 'Pending', 'Completed').
            pdf_path: The filesystem path to the generated resume PDF.
            details: Extracted job description snippet or other textual metadata.
            error_message: Optional error details if processing failed.

        Returns:
            True if the job was successfully updated, False otherwise.
        """
        ...

    def get_all_jobs(self) -> List[Any]:
        """
        Retrieves all jobs from the persistence layer.

        Returns:
            A list of job dictionaries containing status and metadata.
        """
        ...
    
    def add_job(
        self,
        url: str,
        user_id: str,
        status: str = "Pending",
        source_feed: Optional[str] = None,
        source_feed_name: Optional[str] = None,
        job_title: Optional[str] = None
    ) -> bool:
        """
        Adds a new job to the persistence layer.

        Args:
            url: The unique URL of the job posting.
            user_id: The ID of the user the job belongs to.
            status: Initial processing status.
            source_feed: URL of the RSS feed that sourced this job.
            job_title: Title of the job role.

        Returns:
            True if the job was added, False if it already existed.
        """
        ...
    
    def job_exists(self, url: str, user_id: str) -> bool:
        """
        Checks if a job with the given URL already exists for the user.

        Args:
            url: The unique URL of the job.
            user_id: The ID of the user.

        Returns:
            True if the job exists, False otherwise.
        """
        ...
        
class BrowserAgentProtocol(Protocol):
    """
    Protocol defining the requirements for browser automation and scraping.
    
    IMPORTANT: Implementations of this protocol MUST NOT submit applications.
    All form automation must stop before any submit action.
    """
    async def scrape_job_details(self, job_link: str) -> str:
        """
        Navigates to a job link and extracts the full job description.

        Args:
            job_link: The URL of the job posting.

        Returns:
            The extracted job description as a structured string.
        """
        ...

    async def extract_form(self, job_link: str) -> dict:
        """
        Opens a job application form and extracts its structure WITHOUT filling.

        This method discovers form fields and extracts labels/xpaths.
        A separate LLM step generates the answers.

        Args:
            job_link: The URL of the job application form.

        Returns:
            A dict containing form structure with fields, labels, and xpaths.
        """
        ...
    
    async def open_draft(self, job_link: str, form_state: dict) -> dict:
        """
        Opens a saved draft and rehydrates the form from saved state.
        
        This is a deferred action for manual completion. After rehydration,
        browser automation ENDS and the user takes control.

        Args:
            job_link: The URL of the job posting.
            form_state: Previously saved form state with field values.

        Returns:
            A dict with rehydration status and field restoration counts.
        """
        ...

class ResumeBuilderProtocol(Protocol):
    """
    Protocol defining the requirements for tailoring and generating resumes.
    """
    def calculate_ats_score(self, job_description: str, resume_text: str) -> dict:
        """
        Calculates an ATS score for a resume against a job description.
        """
        ...

    def build(self, job_description: str, resume_info: str, job_id: int, template_path: Optional[str] = None, tailoring_prompt: Optional[str] = None, version: str = "v1") -> tuple[str, str]:
        """
        Generates a tailored resume PDF based on a job description.

        Returns:
            A tuple of (pdf_path, tex_path).
        """
        ...


class EventPublisher(Protocol):
    """
    Interface for fire-and-forget event publishing.
    """
    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Publishes an event to potential consumers.

        Args:
            event_type: String identifier for the event (e.g., 'new_job_found').
            data: Payload containing event details.
        """
        ...

class Deduplicator(Protocol):
    """
    Interface for idempotent deduplication of incoming items.
    """
    def is_new(self, key: str, user_id: Optional[str] = None) -> bool:
        """
        Checks if the given key has been seen before for the user.

        Args:
            key: Unique identifier for the item.
            user_id: Optional user context.

        Returns:
            True if the item is new, False otherwise.
        """
        ...

    def mark_seen(self, key: str, user_id: Optional[str] = None) -> None:
        """
        Marks the key as seen to prevent future duplicates.

        Args:
            key: Unique identifier for the item.
            user_id: Optional user context.
        """
        ...

class ConfigManagerProtocol(Protocol):
    """
    Protocol defining the requirements for configuration and feed management.
    """
    def get_feeds(self) -> List[str]:
        """
        Retrieves the list of configured RSS feed URLs.
        """
        ...
