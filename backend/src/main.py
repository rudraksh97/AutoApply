import asyncio
import os
from src.resume_builder import ResumeBuilder
from src.agent import BrowserAgent
from src.rss_watcher import RSSWatcher
from src.config import ConfigManager
from src.job_manager import JobManager
from src.profile_manager import ProfileManager
from dotenv import load_dotenv

load_dotenv()

CURRENT_RESUME_INFO = """
Software Engineer with 5 years of experience in Python, AWS, and Web Development.
Education: BS in Computer Science.
Key Skills: Python, Django, React, Docker, Kubernetes.
"""

async def process_job(job_link, resume_builder, browser_agent, job_manager, user_details_text, log_callback=print):
    log_callback(f"Processing Job: {job_link}")
    job_manager.update_job(job_link, status="Running - Scraping")
    
    try:
        # Step 1: Scrape Job Details
        log_callback("Scraping job details...")
        job_description = await browser_agent.scrape_job_details(job_link)
        job_manager.update_job(job_link, details=job_description[:500] + "...") # Store snippet
        
        # Step 2: Generate Resume
        log_callback("Generating resume...")
        job_manager.update_job(job_link, status="Running - Generating Resume")
        job_id = abs(hash(job_link)) 
        pdf_path = resume_builder.build(job_description, CURRENT_RESUME_INFO, job_id=job_id)
        
        # Update PDF path in DB
        job_manager.update_job(job_link, pdf_path=pdf_path, status="Running - Resume Ready")
        
        # Step 3: Apply (Local File)
        log_callback(f"Applying to job with resume: {pdf_path}")
        job_manager.update_job(job_link, status="Running - Applying")
        
        application_result = await browser_agent.apply_to_job(job_link, pdf_path, user_details_text)
        
        log_callback(f"Application Result: {application_result}")
        job_manager.update_job(job_link, status="Completed")
        return True

    except Exception as e:
        log_callback(f"Error processing job {job_link}: {e}")
        job_manager.update_job(job_link, status="Failed", error_message=str(e))
        return False

async def run_auto_apply(log_callback=print, continuous=False, interval_hours=1, stop_event=None):
    resume_builder = ResumeBuilder()
    
    # Always headless as per user request
    is_headless = True
    browser_agent = BrowserAgent(headless=is_headless)
    
    config_manager = ConfigManager()
    job_manager = JobManager()
    profile_manager = ProfileManager()
    
    # Load user details
    user_details_text = profile_manager.get_profile_as_text()
    
    rss_watcher = RSSWatcher(job_manager)
    rss_watcher.feeds = config_manager.get_feeds()

    while True:
        log_callback("Checking for new jobs...")
        
        # This checks for NEW jobs from RSS and adds them as 'Pending' to the DB
        # It yields them if they were just added
        new_jobs_found = list(rss_watcher.get_new_jobs())
        if new_jobs_found:
             log_callback(f"Found {len(new_jobs_found)} new jobs from RSS feed.")
        
        # NOW, we check the DB for ANY job with status 'Pending' and process it
        # This handles both the just-added jobs and any from previous runs that weren't processed
        all_jobs = job_manager.get_all_jobs()
        pending_jobs = [job for job in all_jobs if job.get('status') == 'Pending']
        
        if not pending_jobs:
            log_callback("No pending jobs to process.")
        else:
            log_callback(f"Processing {len(pending_jobs)} pending jobs...")
            for job in pending_jobs:
                job_link = job['url']
                await process_job(job_link, resume_builder, browser_agent, job_manager, user_details_text, log_callback)

        log_callback("Job check cycle complete.")
        
        if not continuous:
            break
            
        log_callback(f"Waiting 60s before next check...")
        
        # Graceful sleep checking stop_event
        if stop_event:
            try:
               await asyncio.wait_for(stop_event.wait(), timeout=60)
               # If we get here, event was set
               log_callback("Stop signal received.")
               break
            except asyncio.TimeoutError:
               # Timeout reached, continue loop
               pass
        else:
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_auto_apply())
