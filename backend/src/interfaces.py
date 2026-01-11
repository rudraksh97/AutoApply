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
        
class BrowserAgentProtocol(Protocol):
    """
    Protocol defining the requirements for browser automation and scraping.
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

    async def apply_to_job(self, job_link: str, resume_path: str, user_details: str) -> str:
        """
        Navigates to a job link and submits an application using the provided details.

        Args:
            job_link: The URL of the job posting.
            resume_path: The local path to the resume PDF to upload.
            user_details: Textual representation of the user's profile and answers.

        Returns:
            A string describing the result of the application attempt.
        """
        ...

class ResumeBuilderProtocol(Protocol):
    """
    Protocol defining the requirements for tailoring and generating resumes.
    """
    def build(self, job_description: str, resume_info: str, job_id: int) -> str:
        """
        Generates a tailored resume PDF based on a job description.

        Args:
            job_description: The content of the job requirement.
            resume_info: The original base resume/profile information.
            job_id: A unique identifier for the job, used for file naming.

        Returns:
            The absolute path to the generated PDF file.
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
    def is_new(self, key: str) -> bool:
        """
        Checks if the given key has been seen before.

        Args:
            key: Unique identifier for the item.

        Returns:
            True if the item is new, False otherwise.
        """
        ...

    def mark_seen(self, key: str) -> None:
        """
        Marks the key as seen to prevent future duplicates.

        Args:
            key: Unique identifier for the item.
        """
        ...
