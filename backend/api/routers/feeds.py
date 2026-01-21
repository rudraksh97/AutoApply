import re
import os
import json
import logging
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from api.services.domain_services import FeedService
from api.dependencies import get_feed_service
from api.schemas.models import FeedURL, FeedURLOnly

from src.infrastructure import JobManagerEventPublisher, JobManagerDeduplicator
from src.job_manager import JobManager
from src.config import ConfigManager
from src.rss_utils import (
    needs_llm_extraction,
    extract_company_from_feed,
    extract_job_link_with_llm,
    TEST_FEED_PATTERN
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feeds", tags=["Feeds"])



@router.get("/")
def get_feeds(service: FeedService = Depends(get_feed_service)):
    return service.get_feeds()

@router.post("/")
def add_feed(feed: FeedURL, service: FeedService = Depends(get_feed_service)):
    if service.add_feed(feed.url, feed.name):
        return {"status": "added", "url": feed.url, "name": feed.name}
    raise HTTPException(status_code=400, detail="Feed URL or name already exists")

@router.delete("/")
def remove_feed(feed: FeedURLOnly, service: FeedService = Depends(get_feed_service)):
    service.remove_feed(feed.url)
    return {"status": "removed", "url": feed.url}


@router.post("/poll")
async def poll_feeds_now():
    """
    Manually trigger an immediate poll of all configured RSS feeds.
    This bypasses the hourly schedule and fetches new jobs right away.
    Note: Test feeds are skipped - use individual poll for test feeds.
    """
    import feedparser
    import asyncio
    
    job_manager = JobManager()
    config_manager = ConfigManager()
    
    event_publisher = JobManagerEventPublisher(job_manager)
    deduplicator = JobManagerDeduplicator(job_manager)
    
    all_feeds = config_manager.get_feeds()  # Returns list of {url, name} objects
    # Filter out test feeds
    feeds_to_poll = [f for f in all_feeds if TEST_FEED_PATTERN not in f["url"]]
    skipped_feeds = [f for f in all_feeds if TEST_FEED_PATTERN in f["url"]]
    
    if not feeds_to_poll:
        return {
            "status": "no_feeds", 
            "message": "No real RSS feeds configured (test feeds are skipped)", 
            "jobs_found": 0,
            "skipped": skipped_feeds
        }
    
    # Poll each feed manually (instead of using watcher.poll_once which polls all)
    jobs_found = 0
    use_llm = False
    
    for feed_obj in feeds_to_poll:
        feed_url = feed_obj["url"]
        feed_name = feed_obj["name"]
        try:
            loop = asyncio.get_event_loop()
            parsed_feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
            
            # Check if this feed needs LLM-based extraction
            use_llm = needs_llm_extraction(feed_url)
            
            # Try to extract company name from feed title or URL
            feed_title = parsed_feed.feed.get("title", "")
            company_name = extract_company_from_feed(feed_url, feed_title)
            
            for entry in parsed_feed.entries:
                original_link = entry.get("link")
                if not original_link:
                    continue
                
                # Use LLM to extract actual job URL if needed
                if use_llm:
                    extraction = await extract_job_link_with_llm(entry)
                    job_link = extraction.get("job_url")
                    
                    # Skip if no valid job URL found
                    if not job_link:
                        logger.info(f"Skipping entry - no job URL extracted: {entry.get('title', '')[:50]}")
                        continue
                    
                    # Use extracted metadata
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
                    jobs_found += 1
        except Exception as e:
            logger.error(f"Error polling feed {feed_url}: {e}")
    
    return {
        "status": "success",
        "message": f"Polled {len(feeds_to_poll)} feed(s), found {jobs_found} new job(s)",
        "feeds_polled": [f["url"] for f in feeds_to_poll],
        "skipped": [f["url"] for f in skipped_feeds]
    }

@router.post("/poll-single")
async def poll_single_feed(feed: FeedURLOnly):
    """
    Manually trigger an immediate poll of a single RSS feed.
    """
    import feedparser
    import asyncio
    
    job_manager = JobManager()
    config_manager = ConfigManager()
    event_publisher = JobManagerEventPublisher(job_manager)
    deduplicator = JobManagerDeduplicator(job_manager)
    
    feed_url = feed.url
    jobs_found = 0
    
    # Look up feed name from config, or use "Test" for test feed
    feed_name = None
    if TEST_FEED_PATTERN in feed_url:
        feed_name = "Test"
    else:
        all_feeds = config_manager.get_feeds()
        for f in all_feeds:
            if f["url"] == feed_url:
                feed_name = f["name"]
                break
    
    try:
        loop = asyncio.get_event_loop()
        parsed_feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
        
        if parsed_feed.get("bozo"):
            return {
                "status": "warning",
                "message": f"Feed parsed with warnings: {parsed_feed.bozo_exception}",
                "feed": feed_url,
                "jobs_found": 0
            }
        
        # Check if this feed needs LLM-based extraction
        use_llm = _needs_llm_extraction(feed_url)
        
        # Extract company name from feed
        feed_title = parsed_feed.feed.get("title", "")
        company_name = _extract_company_from_feed(feed_url, feed_title)
        
        skipped_entries = 0
        for entry in parsed_feed.entries:
            original_link = entry.get("link")
            if not original_link:
                continue
            
            # Use LLM to extract actual job URL if needed
            if use_llm:
                extraction = await _extract_job_link_with_llm(entry)
                job_link = extraction.get("job_url")
                
                # Skip if no valid job URL found
                if not job_link:
                    logger.info(f"Skipping entry - no job URL extracted: {entry.get('title', '')[:50]}")
                    skipped_entries += 1
                    continue
                
                # Use extracted metadata
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
                jobs_found += 1
        
        result = {
            "status": "success",
            "message": f"Found {jobs_found} new job(s)",
            "feed": feed_url,
            "jobs_found": jobs_found,
            "llm_extraction": use_llm
        }
        if skipped_entries > 0:
            result["skipped_entries"] = skipped_entries
            result["message"] += f" (skipped {skipped_entries} without valid job URLs)"
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to poll feed: {str(e)}")
