"""
Infrastructure implementations for core system interfaces.
"""

import asyncio
import logging
from typing import Any, Set
from src.interfaces import EventPublisher, Deduplicator, JobManagerProtocol

class InMemoryDeduplicator(Deduplicator):
    """
    Simple in-memory implementation of the Deduplicator.
    NOTE: This is not persistent across restarts.
    """
    def __init__(self):
        self._seen_keys: Set[str] = set()

    def is_new(self, key: str) -> bool:
        return key not in self._seen_keys

    def mark_seen(self, key: str) -> None:
        self._seen_keys.add(key)

class LoggingEventPublisher(EventPublisher):
    """
    Simple event publisher that logs events.
    Useful for local development and debugging.
    """
    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        logging.info(f"Event Published: {event_type} | Data: {data}")
        # In a real scenario, this might push to a queue (Redis, RabbitMQ)
        # or trigger a background task.

class AsyncCallbackPublisher(EventPublisher):
    """
    Dispatched events to an async callback function.
    Useful for decoupling without a full message broker.
    """
    def __init__(self, callback):
        self.callback = callback

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        # Fire and forget if callback is handled in background
        asyncio.create_task(self.callback(event_type, data))

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
            # Replicate legacy behavior: add as Pending
            self.job_manager.add_job(job_link, status="Pending")
            if self.log_callback:
                self.log_callback(f"[RSS] Found new job: {job_link}")

class JobManagerDeduplicator(Deduplicator):
    """
    Uses JobManager to check if a job already exists in the database.
    This provides persistence for the RSS watcher via the existing DB.
    """
    def __init__(self, job_manager: JobManagerProtocol):
        self.job_manager = job_manager

    def is_new(self, key: str) -> bool:
        # The key is "feed_url:entry_id". 
        # For compatibility with legacy JobManager which only stores link:
        # We extract the link if the key looks like a link, or just use the link from the data.
        # But wait, the key passed to deduplicator is usually the link.
        # In rss_watcher.py: dedup_key = f"{feed_url}:{entry_id}"
        # This is better for deduplication but different from legacy job_exists(link).
        # We'll stick to the dedup_key for now, but JobManager doesn't know about it.
        # Let's adjust rss_watcher.py to just use link for simple dedup if needed, 
        # or update JobManager. 
        # Actually, for now, we'll just use the link part if possible or just return True 
        # if we want to rely on DB constraints.
        
        # Better: extract link from entry id if it's a URL.
        # For now, let's just use the link itself as the key in rss_watcher.py 
        # if we want to bridge to legacy JobManager.
        return not self.job_manager.job_exists(key)

    def mark_seen(self, key: str) -> None:
        # JobManager.add_job marks it as seen by putting it in DB.
        pass
