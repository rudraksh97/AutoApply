import asyncio
import logging
from typing import Dict

class WorkflowRegistry:
    """
    Tracks active job processing tasks to allow cancellation.
    This is a singleton registry shared between the background loop and API.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkflowRegistry, cls).__new__(cls)
            cls._instance.active_tasks: Dict[str, asyncio.Task] = {}
        return cls._instance

    def register(self, url: str, task: asyncio.Task):
        """Registers a running task for a job URL."""
        self.active_tasks[url] = task
        # logging.info(f"[Registry] Registered task for {url}")

    def unregister(self, url: str):
        """Unregisters a task (called upon completion or error)."""
        if url in self.active_tasks:
            del self.active_tasks[url]
            # logging.info(f"[Registry] Unregistered task for {url}")

    def cancel(self, url: str) -> bool:
        """Cancels a running task for a job URL if it exists."""
        if url in self.active_tasks:
            task = self.active_tasks[url]
            if not task.done():
                task.cancel()
                logging.info(f"[Registry] Cancelled active task for {url}")
                return True
        return False

    def is_running(self, url: str) -> bool:
        """Checks if a job URL has an active task."""
        return url in self.active_tasks and not self.active_tasks[url].done()
