"""
FastAPI server for the AutoApply application.

This module provides:
- REST API endpoints for job management, feeds, profiles, and drafts
- Background task for automated RSS polling and job processing
- Static file serving for resumes and generated documents
"""

import asyncio
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routers import drafts, feeds, jobs, profile, settings, test_feed
from src.agent import BrowserAgent
from src.config import ConfigManager
from src.infrastructure import JobManagerDeduplicator, JobManagerEventPublisher
from src.job_manager import JobManager
from src.resume_builder import ResumeBuilder
from src.services import DraftPreparationService, get_user_profile_text
from src.rss_utils import (
    needs_llm_extraction,
    extract_company_from_feed,
    extract_job_link_with_llm,
    TEST_FEED_PATTERN
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[
        logging.StreamHandler()
    ]
)


# =============================================================================
# Constants
# =============================================================================

DATA_DIRECTORIES = [
    "data/resumes",
    "data/resumes/templates",
    "data/generated_resumes",
    "data/tex_resumes",
]

# =============================================================================
# Background Tasks
# =============================================================================

# Background automation loop removed - moved to backend/poll_worker.py microservice


async def _poll_rss_feeds(config_manager, event_publisher, deduplicator):
    """Poll all configured RSS feeds for new jobs."""
    import feedparser

    logging.info("Triggering periodic RSS poll...")
    all_feeds = config_manager.get_feeds()
    feeds_to_poll = [f for f in all_feeds if TEST_FEED_PATTERN not in f["url"]]
    logging.info(f"Feeds to poll: {feeds_to_poll}")
    logging.info(f"-------------------------------------------------------------------------------------")
    for feed_obj in feeds_to_poll:
        logging.info(f"#####################################################################################")
        logging.info(f"Processing feed: {feed_obj}")
        feed_url = feed_obj["url"]
        feed_name = feed_obj["name"]

        try:
            logging.info(f"Starting to process feed: {feed_url}")
            loop = asyncio.get_event_loop()
            parsed_feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
            logging.info(f"Parsed feed: {parsed_feed}")
            use_llm = needs_llm_extraction(feed_url)
            feed_title = parsed_feed.feed.get("title", "")
            company_name = extract_company_from_feed(feed_url, feed_title)

            for entry in parsed_feed.entries:
                logging.info(f"Processing feed entry: {entry}")
                await _process_feed_entry(
                    entry, feed_url, feed_name, company_name,
                    use_llm, event_publisher, deduplicator
                )
                logging.info(f"Processed feed entry: {entry}")
            logging.info(f"Ended Processed feed: {feed_url}")

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logging.error(f"Error polling feed {feed_url}: {e}\nStack trace:\n{tb}")

    logging.info(f"RSS poll complete. Polled {len(feeds_to_poll)} feed(s).")


async def _process_feed_entry(
    entry, feed_url, feed_name, company_name,
    use_llm, event_publisher, deduplicator
):
    """Process a single RSS feed entry."""
    original_link = entry.get("link")
    if not original_link:
        return

    if use_llm:
        extraction = await extract_job_link_with_llm(entry)
        job_link = extraction.get("job_url")
        if not job_link:
            logging.debug(f"Skipping - no job URL: {entry.get('title', '')[:50]}")
            return
        job_title = extraction.get("job_title") or entry.get("title", "Unknown")
        entry_company = extraction.get("company_name") or company_name
    else:
        job_link = original_link
        job_title = entry.get("title", "Unknown")
        entry_company = entry.get("author") or entry.get("dc_creator") or company_name

    if deduplicator.is_new(job_link):
        await event_publisher.publish("new_job_ingested", {
            "job_link": job_link,
            "title": job_title,
            "feed_url": feed_url,
            "feed_name": feed_name,
            "company_name": entry_company
        })
        deduplicator.mark_seen(job_link)


async def _process_pending_jobs(job_manager, service):
    """Process all jobs with 'Pending' or 'Retried' status."""
    all_jobs = job_manager.get_all_jobs()
    # Pick up both Pending (new) and Retried (requested retry)
    processing_jobs = [j for j in all_jobs if j.get('status') in ['Pending', 'Retried']]

    if not processing_jobs:
        logging.debug("No jobs to process.")
        return
    
    logging.info(f"Processing {len(processing_jobs)} jobs...")

    for job in processing_jobs:
        url = job.get('url')
        status = job.get('status')
        
        if url:
            # If it's a retry, increment the counter
            if status == 'Retried':
                logging.info(f"🔄 Incrementing retry count for: {url}")
                job_manager.increment_retry_count(url)

            logging.info(f"🚀 Processing: {url}")
            user_profile_text = get_user_profile_text()
            await service.prepare_draft(url, user_profile_text, log_callback=logging.info)


# =============================================================================
# Application Setup
# =============================================================================

def _ensure_directories():
    """Create required data directories."""
    for directory in DATA_DIRECTORIES:
        os.makedirs(directory, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    _ensure_directories()

    # Safety: Ensure Job Manager is stopped on startup
    from src.job_manager_state import JobManagerState
    if JobManagerState.is_running():
        logging.info("Forcing Job Manager to STOPPED state on startup safety check.")
        JobManagerState.set_running(False)

    # task = asyncio.create_task(automation_loop())
    yield
    # task.cancel()

    # try:
    #     await task
    # except asyncio.CancelledError:
    #     logging.info("Background automation task stopped.")


app = FastAPI(
    title="AutoApply API",
    version="2.0.0",
    description="Draft-first job application preparation.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(feeds.router)
app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(drafts.router)
app.include_router(settings.router)
app.include_router(test_feed.router)

# Static Files
_ensure_directories()
app.mount("/data", StaticFiles(directory="data"), name="data")
app.mount("/resumes", StaticFiles(directory="data/resumes"), name="resumes")
app.mount("/generated_resumes", StaticFiles(directory="data/generated_resumes"), name="generated_resumes")
app.mount("/tex_resumes", StaticFiles(directory="data/tex_resumes"), name="tex_resumes")


# =============================================================================
# Upload Endpoints
# =============================================================================

@app.post("/upload-template", tags=["Settings"])
async def upload_template(file: UploadFile = File(...)):
    """Upload a LaTeX resume template."""
    if not file.filename.endswith(".tex"):
        raise HTTPException(status_code=400, detail="Only .tex files allowed")

    save_path = f"data/resumes/templates/{file.filename}"
    content = await file.read()

    with open(save_path, "wb") as f:
        f.write(content)

    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    resume_id = pm.add_resume("text", file.filename, save_path)

    profile = pm.get_profile()
    profile["custom_template_filename"] = file.filename
    pm.save_profile(profile)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "path": save_path,
        "resume_id": resume_id
    }


@app.post("/upload-resume", tags=["Settings"])
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume (PDF or LaTeX)."""
    is_pdf = file.filename.endswith(".pdf")
    is_tex = file.filename.endswith(".tex")

    if not (is_pdf or is_tex):
        raise HTTPException(status_code=400, detail="Only .pdf or .tex files allowed")

    save_dir = "data/resumes" if is_pdf else "data/resumes/templates"
    save_path = f"{save_dir}/{file.filename}"
    content = await file.read()

    with open(save_path, "wb") as f:
        f.write(content)

    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    resume_type = "pdf" if is_pdf else "text"
    resume_id = pm.add_resume(resume_type, file.filename, save_path)

    profile = pm.get_profile()
    if is_pdf:
        profile["resume_generation_mode"] = "uploaded_pdf"
    else:
        profile["resume_generation_mode"] = "ats_generated"
        profile["custom_template_filename"] = file.filename
    pm.save_profile(profile)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "path": save_path,
        "resume_id": resume_id
    }


@app.post("/parse-resume", tags=["Settings"])
async def parse_resume(source: str = "pdf"):
    """Parse an uploaded resume to extract profile data."""
    from src.profile_manager import ProfileManager
    from src.resume_parser import ResumeParser

    pm = ProfileManager()

    resume_type = "text" if source == "tex" else "pdf"
    file_path = pm.get_current_resume_path(resume_type)

    if not file_path or not os.path.exists(file_path):
        file_type = "LaTeX" if source == "tex" else "PDF"
        raise HTTPException(
            status_code=400,
            detail=f"No selected {file_type} resume found. Please upload and select one first."
        )

    try:
        parser = ResumeParser()
        return await parser.parse_file(file_path)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logging.error(f"Resume parsing error: {e}\nStack trace:\n{tb}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
