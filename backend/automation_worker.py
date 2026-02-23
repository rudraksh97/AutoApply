import asyncio
import logging
import os
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("JobAutomationWorker")

# Ensure src can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.db import SessionLocal
from src.job_manager import JobManager
from src.resume_builder import ResumeBuilder
from src.services import DraftPreparationService
from src.agent import BrowserAgent
from api.repositories.sql_repo import SqlProfileRepository
from api.services.domain_services import ProfileService
from src.job_manager_state import JobManagerState
from src.models import Job

async def automation_loop():
    """Background loop to process pending jobs (Draft Creation)."""
    logger.info("Starting Job Automation Worker...")
    
    job_manager = JobManager()
    browser_agent = BrowserAgent(headless=True)
    
    while True:
        try:
            # Check if Job Manager is enabled
            if not JobManagerState.is_running():
                logger.info("Job Manager is paused. Skipping automation loop...")
                await asyncio.sleep(15)
                continue

            db = SessionLocal()
            profile_repo = SqlProfileRepository(db)
            profile_service = ProfileService(profile_repo)
            resume_builder = ResumeBuilder()
            
            service = DraftPreparationService(
                job_manager=job_manager,
                browser_agent=browser_agent,
                resume_builder=resume_builder,
                profile_service=profile_service
            )
            
            # 1. Get pending jobs from DB directly to get user_id
            pending_jobs = db.query(Job).filter(Job.status.in_(['PENDING', 'RETRIED'])).all()
            
            if pending_jobs:
                logger.info(f"Processing {len(pending_jobs)} pending jobs...")
            
            for job in pending_jobs:
                try:
                    user_id = job.user_id
                    url = job.url
                    status = job.status
                    
                    if status == 'RETRIED':
                        job.retry_count = (job.retry_count or 0) + 1
                        db.commit() # Commit retry increment
                    
                    logger.info(f"🚀 Processing: {url} for user {user_id}")
                    
                    # DraftPreparationService.prepare_draft is async
                    await service.prepare_draft(url, user_id, log_callback=logger.info)
                    
                except Exception as e:
                    logger.error(f"Error processing job {job.url}: {e}")
                    job.status = 'Failed'
                    job.error_message = str(e)
                    db.commit()
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error in automation loop: {e}")
            
        await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(automation_loop())
    except KeyboardInterrupt:
        logger.info("Job Automation Worker stopped.")
