"""
Infrastructure implementations for core system interfaces.
"""

import asyncio
import logging
from typing import Any, Set
from src.interfaces import EventPublisher, Deduplicator, JobManagerProtocol

class JobManagerEventPublisher(EventPublisher):
    """
    Bridges RSS ingestion events to the JobManager persistence layer.
    """
    def __init__(self, job_manager: JobManagerProtocol, log_callback=None):
        self.job_manager = job_manager
        self.log_callback = log_callback

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        if event_type == "new_job_ingested":
            job_link = data["job_link"]
            job_title = data.get("title")
            feed_url = data.get("feed_url")
            company_name = data.get("company_name")
            
            # Add job with metadata
            self.job_manager.add_job(
                job_link, 
                status="Pending",
                source_feed=feed_url,
                company_name=company_name,
                job_title=job_title
            )
            if self.log_callback:
                self.log_callback(f"[RSS] Found new job: {job_title or job_link}")

class JobManagerDeduplicator(Deduplicator):
    """
    Uses JobManager to check if a job already exists in the database.
    This provides persistence for the RSS watcher via the existing DB.
    """
    def __init__(self, job_manager: JobManagerProtocol):
        self.job_manager = job_manager

    def is_new(self, key: str) -> bool:
        return not self.job_manager.job_exists(key)

    def mark_seen(self, key: str) -> None:
        # JobManager.add_job marks it as seen by putting it in DB.
        pass
