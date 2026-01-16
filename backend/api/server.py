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
from langchain_openai import ChatOpenAI

from api.routers import drafts, feeds, jobs, profile, settings, test_feed
from src.agent import BrowserAgent
from src.config import ConfigManager
from src.infrastructure import JobManagerDeduplicator, JobManagerEventPublisher
from src.job_manager import JobManager
from src.prompts import EXTRACT_JOB_LINK_FROM_RSS_PROMPT
from src.resume_builder import ResumeBuilder
from src.services import DraftPreparationService, get_user_profile_text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# =============================================================================
# Constants
# =============================================================================

TEST_FEED_PATTERN = "/test/feed.xml"

AGGREGATOR_FEED_PATTERNS = [
    "hnrss.org",
    "news.ycombinator.com",
    "reddit.com",
    "lobste.rs",
]

DATA_DIRECTORIES = [
    "data/resumes",
    "data/resumes/templates",
    "data/generated_resumes",
    "data/tex_resumes",
]


# =============================================================================
# Feed Processing Helpers
# =============================================================================

def _needs_llm_extraction(feed_url: str) -> bool:
    """Check if this feed needs LLM-based job link extraction."""
    return any(pattern in feed_url.lower() for pattern in AGGREGATOR_FEED_PATTERNS)


async def _extract_job_link_with_llm(entry: dict) -> dict:
    """Use LLM to extract the actual job application URL from an RSS entry."""
    entry_title = entry.get("title", "")
    entry_link = entry.get("link", "")
    entry_description = entry.get("description", "") or entry.get("summary", "")

    if not entry_description and entry.get("content"):
        content_list = entry.get("content", [])
        if content_list:
            entry_description = content_list[0].get("value", "")

    prompt = EXTRACT_JOB_LINK_FROM_RSS_PROMPT.format(
        entry_title=entry_title,
        entry_description=entry_description[:3000],
        entry_link=entry_link
    )

    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return {"job_url": entry_link, "company_name": None, "job_title": entry_title}

        config = ConfigManager()
        llm = ChatOpenAI(
            model=config.get_selected_model(),
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1
        )

        response = await llm.ainvoke(prompt)
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

    except Exception as e:
        logging.error(f"LLM extraction failed: {e}")

    return {"job_url": None, "company_name": None, "job_title": entry_title}


def _extract_company_from_feed(feed_url: str, feed_title: str) -> str:
    """Extract company name from feed URL or title."""
    # Try from feed title first
    if feed_title:
        company = re.sub(
            r'\s*(Jobs|Careers|RSS|Feed|Openings).*$',
            '',
            feed_title,
            flags=re.IGNORECASE
        ).strip()
        if company:
            return company

    # Try from URL patterns
    parsed = urlparse(feed_url)
    domain = parsed.netloc.lower()

    patterns = [
        (r'greenhouse\.io/(\w+)', "greenhouse.io"),
        (r'ashbyhq\.com/([^/]+)', "ashbyhq.com"),
        (r'lever\.co/([^/]+)', "lever.co"),
        (r'apply\.workable\.com/([^/]+)', "workable.com"),
    ]

    for pattern, domain_match in patterns:
        if domain_match in domain:
            match = re.search(pattern, feed_url)
            if match:
                return match.group(1).replace('-', ' ').title()

    # Fallback: use cleaned domain
    domain = re.sub(r'^(www\.|jobs\.|careers\.|boards\.)', '', domain)
    domain = domain.split('.')[0]
    return domain.replace('-', ' ').title() if domain else None


# =============================================================================
# Background Tasks
# =============================================================================

async def automation_loop():
    """Background task to poll RSS feeds and process pending jobs."""
    logging.info("Starting background automation task...")

    job_manager = JobManager()
    config_manager = ConfigManager()
    agent = BrowserAgent(headless=True)
    builder = ResumeBuilder()
    service = DraftPreparationService(job_manager, agent, builder)

    event_publisher = JobManagerEventPublisher(job_manager)
    deduplicator = JobManagerDeduplicator(job_manager)

    last_rss_poll = 0

    while True:
        try:
            now = time.time()

            # Poll RSS feeds hourly
            if now - last_rss_poll > 3600:
                await _poll_rss_feeds(
                    config_manager, event_publisher, deduplicator
                )
                last_rss_poll = now

            # Process pending jobs every minute
            await _process_pending_jobs(job_manager, service)

        except Exception as e:
            logging.error(f"Error in automation loop: {e}")

        await asyncio.sleep(60)


async def _poll_rss_feeds(config_manager, event_publisher, deduplicator):
    """Poll all configured RSS feeds for new jobs."""
    import feedparser

    logging.info("Triggering periodic RSS poll...")
    all_feeds = config_manager.get_feeds()
    feeds_to_poll = [f for f in all_feeds if TEST_FEED_PATTERN not in f["url"]]

    for feed_obj in feeds_to_poll:
        feed_url = feed_obj["url"]
        feed_name = feed_obj["name"]

        try:
            loop = asyncio.get_event_loop()
            parsed_feed = await loop.run_in_executor(None, feedparser.parse, feed_url)

            use_llm = _needs_llm_extraction(feed_url)
            feed_title = parsed_feed.feed.get("title", "")
            company_name = _extract_company_from_feed(feed_url, feed_title)

            for entry in parsed_feed.entries:
                await _process_feed_entry(
                    entry, feed_url, feed_name, company_name,
                    use_llm, event_publisher, deduplicator
                )

        except Exception as e:
            logging.error(f"Error polling feed {feed_url}: {e}")

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
        extraction = await _extract_job_link_with_llm(entry)
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
    """Process all jobs with 'Pending' status."""
    all_jobs = job_manager.get_all_jobs()
    pending_jobs = [j for j in all_jobs if j.get('status') == 'Pending']

    if not pending_jobs:
        logging.debug("No pending jobs to process.")
        return

    logging.info(f"Processing {len(pending_jobs)} pending jobs...")

    for job in pending_jobs:
        url = job.get('url')
        if url:
            logging.info(f"Processing: {url}")
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

    task = asyncio.create_task(automation_loop())
    yield
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        logging.info("Background automation task stopped.")


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
        logging.error(f"Resume parsing error: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
