"""
Entry point for the AutoApply application.

This module initializes the application and runs the main orchestration loop
which polls for new jobs from RSS feeds and processes them using the service layer.
"""

import asyncio
import logging
from typing import Optional

from src.resume_builder import ResumeBuilder
from src.agent import BrowserAgent
from src.rss_watcher import RSSWatcher
from src.config import ConfigManager
from src.job_manager import JobManager
from src.profile_manager import ProfileManager
from src.services import JobApplicationService
from dotenv import load_dotenv

load_dotenv()

async def run_auto_apply(
    log_callback: Optional[callable] = print, 
    continuous: bool = False, 
    interval_hours: int = 1, 
    stop_event: Optional[asyncio.Event] = None
):
    """
    Main orchestration loop for the AutoApply application.

    This function wires up the core components (Config, Storage, Agent) and 
    periodically triggers a job check cycle. It pulls new jobs from RSS feeds
    and processes any job marked as 'Pending' in the database.

    Args:
        log_callback: Functional callback for real-time status logging.
        continuous: If True, the loop runs indefinitely with a sleep interval.
        interval_hours: Not currently used for timing, but intended for long-poll config.
        stop_event: Optional asyncio Event to gracefully stop the continuous loop.
    """
    # 1. Initialize core components
    config_manager = ConfigManager()
    job_manager = JobManager()
    profile_manager = ProfileManager()
    
    resume_builder = ResumeBuilder()
    browser_agent = BrowserAgent(headless=True) # Always headless as per user request
    
    # 2. Initialize Service Layer
    job_service = JobApplicationService(
        job_manager=job_manager,
        browser_agent=browser_agent,
        resume_builder=resume_builder
    )
    
    # 3. Initialize RSS Watcher Infrastructure
    from src.infrastructure import JobManagerEventPublisher, JobManagerDeduplicator
    event_publisher = JobManagerEventPublisher(job_manager, log_callback=log_callback)
    deduplicator = JobManagerDeduplicator(job_manager)
    
    rss_watcher = RSSWatcher(
        event_publisher=event_publisher,
        deduplicator=deduplicator,
        config_manager=config_manager
    )

    # 4. Load user details once per cycle (or once for the run)
    user_details_text = profile_manager.get_profile_as_text()

    while True:
        log_callback("Checking for new jobs...")
        
        # Pull new jobs from RSS into the database (via events)
        await rss_watcher.poll_once()
        
        # Process all pending jobs from the database
        all_jobs = job_manager.get_all_jobs()
        pending_jobs = [job for job in all_jobs if job.get('status') == 'Pending']
        
        if not pending_jobs:
            log_callback("No pending jobs to process.")
        else:
            log_callback(f"Processing {len(pending_jobs)} pending jobs...")
            for job in pending_jobs:
                await job_service.process_job(
                    job_link=job['url'], 
                    user_details_text=user_details_text, 
                    log_callback=log_callback
                )

        log_callback("Job check cycle complete.")
        
        if not continuous:
            break
            
        log_callback(f"Waiting 60s before next check...")
        
        # Graceful sleep checking stop_event
        if stop_event:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=60)
                log_callback("Stop signal received.")
                break
            except asyncio.TimeoutError:
                pass
        else:
            await asyncio.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_auto_apply())


