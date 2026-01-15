import os
import re
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import time

# Core logic for background polling & processing
from src.rss_watcher import RSSWatcher
from src.infrastructure import JobManagerEventPublisher, JobManagerDeduplicator
from src.job_manager import JobManager
from src.config import ConfigManager
from src.services import JobApplicationService, get_user_profile_text
from src.agent import BrowserAgent
from src.resume_builder import ResumeBuilder
from src.prompts import EXTRACT_JOB_LINK_FROM_RSS_PROMPT

# Routers
from api.routers import feeds, jobs, profile, drafts, settings, test_feed


# Test feed pattern to skip during automatic polling
TEST_FEED_PATTERN = "/test/feed.xml"

# Aggregator feeds that need LLM extraction
AGGREGATOR_FEED_PATTERNS = [
    "hnrss.org",
    "news.ycombinator.com",
    "reddit.com",
    "lobste.rs",
]

def _needs_llm_extraction(feed_url: str) -> bool:
    """Check if this feed needs LLM-based job link extraction."""
    return any(pattern in feed_url.lower() for pattern in AGGREGATOR_FEED_PATTERNS)

async def _extract_job_link_with_llm(entry: dict) -> dict:
    """Use LLM to extract the actual job application URL from an RSS entry."""
    from langchain_openai import ChatOpenAI
    
    entry_title = entry.get("title", "")
    entry_link = entry.get("link", "")
    entry_description = entry.get("description", "") or entry.get("summary", "")
    
    if not entry_description and entry.get("content"):
        content_list = entry.get("content", [])
        if content_list and len(content_list) > 0:
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
        
        llm = ChatOpenAI(
            model="google/gemini-2.0-flash-001",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1
        )
        
        response = await llm.ainvoke(prompt)
        response_text = response.content
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        logging.error(f"LLM extraction failed: {e}")
    
    return {"job_url": None, "company_name": None, "job_title": entry_title}


def _extract_company_from_feed(feed_url: str, feed_title: str) -> str:
    """Extract company name from feed URL or title."""
    # Try from feed title first
    if feed_title:
        company = re.sub(r'\s*(Jobs|Careers|RSS|Feed|Openings).*$', '', feed_title, flags=re.IGNORECASE).strip()
        if company:
            return company
    
    # Try from URL
    parsed = urlparse(feed_url)
    domain = parsed.netloc.lower()
    
    # Extract from common job board patterns
    if "greenhouse.io" in domain:
        match = re.search(r'greenhouse\.io/(\w+)', feed_url)
        if match:
            return match.group(1).replace('-', ' ').title()
    elif "ashbyhq.com" in domain:
        match = re.search(r'ashbyhq\.com/([^/]+)', feed_url)
        if match:
            return match.group(1).replace('-', ' ').title()
    elif "lever.co" in domain:
        match = re.search(r'lever\.co/([^/]+)', feed_url)
        if match:
            return match.group(1).replace('-', ' ').title()
    elif "workable.com" in domain:
        match = re.search(r'apply\.workable\.com/([^/]+)', feed_url)
        if match:
            return match.group(1).replace('-', ' ').title()
    
    # Fallback: use domain without common prefixes
    domain = re.sub(r'^(www\.|jobs\.|careers\.|boards\.)', '', domain)
    domain = domain.split('.')[0]
    return domain.replace('-', ' ').title() if domain else None

# --- Background Tasks ---
async def automation_loop():
    """Background task to poll RSS feeds (hourly) and process pending jobs (minutely)."""
    logging.info("Starting background automation task...")
    
    job_manager = JobManager()
    config_manager = ConfigManager()
    
    # Dependencies for processing
    # BrowserAgent handles its own browser instance
    agent = BrowserAgent(headless=True)
    builder = ResumeBuilder()
    service = JobApplicationService(job_manager, agent, builder)
    
    # Dependencies for polling
    event_publisher = JobManagerEventPublisher(job_manager)
    deduplicator = JobManagerDeduplicator(job_manager)
    
    last_rss_poll = 0
    
    while True:
        try:
            now = time.time()
            
            # 1. Periodic RSS Poll (Hourly) - skip test feeds
            if now - last_rss_poll > 3600:
                logging.info("Triggering periodic RSS poll...")
                all_feeds = config_manager.get_feeds()  # Returns list of {url, name} objects
                feeds_to_poll = [f for f in all_feeds if TEST_FEED_PATTERN not in f["url"]]
                
                if feeds_to_poll:
                    import feedparser
                    for feed_obj in feeds_to_poll:
                        feed_url = feed_obj["url"]
                        feed_name = feed_obj["name"]
                        try:
                            loop = asyncio.get_event_loop()
                            parsed_feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
                            
                            # Check if this feed needs LLM-based extraction
                            use_llm = _needs_llm_extraction(feed_url)
                            
                            # Extract company name from feed
                            feed_title = parsed_feed.feed.get("title", "")
                            company_name = _extract_company_from_feed(feed_url, feed_title)
                            
                            for entry in parsed_feed.entries:
                                original_link = entry.get("link")
                                if not original_link:
                                    continue
                                
                                # Use LLM to extract actual job URL if needed
                                if use_llm:
                                    extraction = await _extract_job_link_with_llm(entry)
                                    job_link = extraction.get("job_url")
                                    
                                    if not job_link:
                                        logging.debug(f"Skipping entry - no job URL: {entry.get('title', '')[:50]}")
                                        continue
                                    
                                    job_title = extraction.get("job_title") or entry.get("title", "Unknown Title")
                                    entry_company = extraction.get("company_name") or company_name
                                else:
                                    job_link = original_link
                                    job_title = entry.get("title", "Unknown Title")
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
                        except Exception as e:
                            logging.error(f"Error polling feed {feed_url}: {e}")
                
                last_rss_poll = now
                logging.info(f"Periodic RSS poll complete. Polled {len(feeds_to_poll)} feed(s).")
            
            # 2. Process Pending Jobs (Every minute)
            all_jobs = job_manager.get_all_jobs()
            pending_jobs = [j for j in all_jobs if j.get('status') == 'Pending']
            
            if pending_jobs:
                logging.info(f"Processing {len(pending_jobs)} pending jobs...")
                for job in pending_jobs:
                    url = job.get('url')
                    if url:
                        logging.info(f"Automated processing start for: {url}")
                        user_profile_text = get_user_profile_text()
                        await service.process_job(url, user_profile_text, log_callback=logging.info)
            else:
                logging.debug("No pending jobs to process.")
                
        except Exception as e:
            logging.error(f"Error in automation loop: {e}")
        
        await asyncio.sleep(60) # Check every minute for pending jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migration: consolidate LaTeX templates
    tex_dir = "data/tex_resumes"
    if not os.path.exists(tex_dir):
        os.makedirs(tex_dir)
    
    # Check common old locations
    old_locations = ["data/resume_base.tex", "data/resumes/resume_base.tex"]
    for loc in old_locations:
        if os.path.exists(loc):
            import shutil
            target = os.path.join(tex_dir, "resume_base.tex")
            if not os.path.exists(target):
                logging.info(f"Migrating {loc} to {target}")
                shutil.move(loc, target)
            else:
                logging.info(f"Default template already exists in {target}, deleting old {loc}")
                os.remove(loc)

    # Start background task
    task = asyncio.create_task(automation_loop())
    yield
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logging.info("Background automation task stopped.")

# --- Application ---
app = FastAPI(
    title="AutoApply API", 
    version="2.0.0",
    description="Draft-first job application preparation (Background Automated).",
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
if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists("data/resumes"):
    os.makedirs("data/resumes")
if not os.path.exists("data/tex_resumes"):
    os.makedirs("data/tex_resumes")
app.mount("/data", StaticFiles(directory="data"), name="data")

# --- Specialized Endpoints (Upload, Control, Websockets) ---

@app.post("/upload-template", tags=["Settings"])
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.endswith(".tex"):
         raise HTTPException(status_code=400, detail="Only .tex files allowed")
    
    save_dir = "data/tex_resumes"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    save_path = f"{save_dir}/{file.filename}"
    content = await file.read()
    
    with open(save_path, "wb") as f:
        f.write(content)
        
    # Also keep as base template for the tailoring engine if needed
    # But primarily we update the profile's tex path
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    profile["uploaded_tex_path"] = save_path
    profile["uploaded_tex_filename"] = file.filename
    profile["custom_template_filename"] = file.filename
    pm.save_profile(profile)
    
    return {"status": "uploaded", "filename": file.filename, "path": save_path}

@app.post("/upload-resume", tags=["Settings"])
async def upload_resume(file: UploadFile = File(...)):
    is_pdf = file.filename.endswith(".pdf")
    is_tex = file.filename.endswith(".tex")
    
    if not (is_pdf or is_tex):
         raise HTTPException(status_code=400, detail="Only .pdf or .tex files allowed")
    
    save_dir = "data/resumes" if is_pdf else "data/tex_resumes"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    save_path = f"{save_dir}/{file.filename}"
    content = await file.read()
    
    with open(save_path, "wb") as f:
        f.write(content)
        
    # Update profile
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    
    if is_pdf:
        profile["uploaded_pdf_path"] = save_path
        profile["uploaded_pdf_filename"] = file.filename
        profile["resume_generation_mode"] = "uploaded_pdf"
    else:
        profile["uploaded_tex_path"] = save_path
        profile["uploaded_tex_filename"] = file.filename
        profile["resume_generation_mode"] = "ats_generated"
        profile["custom_template_filename"] = file.filename
    
    pm.save_profile(profile)
    
    return {"status": "uploaded", "filename": file.filename, "path": save_path}

@app.post("/parse-resume", tags=["Settings"])
async def parse_resume(source: str = "pdf"):
    from src.profile_manager import ProfileManager
    pm = ProfileManager()
    profile = pm.get_profile()
    
    file_path = None
    
    if source == "tex":
        file_path = profile.get("uploaded_tex_path")
        if not file_path or not os.path.exists(file_path):
             # Fallback to base template if exists
             base_path = "data/tex_resumes/resume_base.tex"
             if os.path.exists(base_path):
                 file_path = base_path
             else:
                 raise HTTPException(status_code=400, detail="No uploaded LaTeX template found.")
    else:
        # Default to pdf
        file_path = profile.get("uploaded_pdf_path")
        if not file_path or not os.path.exists(file_path):
             raise HTTPException(status_code=400, detail="No uploaded PDF resume found. Please upload one first.")

    # Parse with ResumeParser
    try:
        from src.resume_parser import ResumeParser
        parser = ResumeParser()
        return await parser.parse_file(file_path)
    except Exception as e:
        print(f"Resume Parsing Error: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
