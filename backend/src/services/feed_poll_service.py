import logging
import feedparser
import asyncio
import time
import json
import os
from typing import List, Dict, Any, Optional

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

class FeedPollService:
    """
    Service to handle polling of RSS feeds for new jobs.
    Encapsulates logic for fetching, parsing, LLM extraction, and deduplication.
    """
    
    # File path for shared status
    STATUS_FILE = "data/poller_status.json"
    
    # Singleton-like state for tracking background task status
    # (Used by the Worker process before writing to file)
    _last_poll_time = 0
    _total_polls = 0
    _last_jobs_found = 0
    _is_polling = False

    def __init__(self):
        self.job_manager = JobManager()
        self.config_manager = ConfigManager()
        self.event_publisher = JobManagerEventPublisher(self.job_manager)
        self.deduplicator = JobManagerDeduplicator(self.job_manager)

    async def poll_all_feeds(self) -> Dict[str, Any]:
        """
        Polls all configured RSS feeds (skipping test feeds) for new jobs.
        """
        FeedPollService._is_polling = True
        try:
            all_feeds = self.config_manager.get_feeds()
            logger.info(f"All feeds: {all_feeds}")
            # Filter out test feeds for the "Poll All" action
            feeds_to_poll = [f for f in all_feeds if TEST_FEED_PATTERN not in f["url"]]
            skipped_feeds = [f for f in all_feeds if TEST_FEED_PATTERN in f["url"]]
            logger.info(f"Feeds to poll: {feeds_to_poll}")
            logger.info(f"Skipped feeds: {skipped_feeds}")
            if not feeds_to_poll:
                return {
                    "status": "no_feeds", 
                    "message": "No real RSS feeds configured (test feeds are skipped)", 
                    "jobs_found": 0,
                    "skipped": skipped_feeds
                }
            
            jobs_found = 0
            feeds_polled = []
            logger.info(f"Feeds to poll: {feeds_to_poll}")
            for feed_obj in feeds_to_poll:
                logger.info(f"Polling feed: {feed_obj['url']}")
                result = await self.poll_feed(feed_obj["url"], feed_obj["name"])
                if result.get("status") == "success":
                    jobs_found += result.get("jobs_found", 0)
                    feeds_polled.append(feed_obj["url"])
                else:
                    logger.warning(f"Failed to poll {feed_obj['url']}: {result.get('message')}")

            # Update stats (write to file)
            FeedPollService._last_poll_time = time.time()
            FeedPollService._total_polls += 1
            FeedPollService._last_jobs_found = jobs_found
            logger.info(f"Jobs found: {jobs_found}")
            FeedPollService._save_status_to_file()

            return {
                "status": "success",
                "message": f"Polled {len(feeds_to_poll)} feed(s), found {jobs_found} new job(s)",
                "feeds_polled": feeds_polled,
                "jobs_found": jobs_found,
                "skipped": [f["url"] for f in skipped_feeds]
            }
            
        finally:
            FeedPollService._is_polling = False
            FeedPollService._save_status_to_file()

    @classmethod
    def _save_status_to_file(cls):
        """Writes current status to the shared JSON file."""
        status_data = {
            "last_poll_time": cls._last_poll_time,
            "total_polls": cls._total_polls,
            "last_jobs_found": cls._last_jobs_found,
            "is_polling": cls._is_polling
        }
        
        try:
            with open(cls.STATUS_FILE, 'w') as f:
                json.dump(status_data, f)
        except Exception as e:
            logger.error(f"Failed to write poller status: {e}")

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Get the current status of the background poller (reads from file)."""
        # Try to read from file first (for the API to see Worker's status)
        if os.path.exists(FeedPollService.STATUS_FILE):
            try:
                with open(FeedPollService.STATUS_FILE, 'r') as f:
                     return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read poller status: {e}")
        
        # Fallback to defaults
        return {
            "last_poll_time": 0,
            "total_polls": 0,
            "last_jobs_found": 0,
            "is_polling": False
        }

    async def poll_feed(self, feed_url: str, feed_name: str = None) -> Dict[str, Any]:
        """
        Polls a single RSS feed.
        """
        # Handle Test Feed URL mapping
        if TEST_FEED_PATTERN in feed_url:
            logger.info(f"Polling test feed: {feed_url}")
            feed_name = "Test" if not feed_name else feed_name
            # Fix: Map relative frontend URL to absolute backend URL for feedparser
            real_feed_url = "http://localhost:8000/test/feed.xml"
        else:
            real_feed_url = feed_url
            logger.info(f"Polling feed: {real_feed_url}")
            # If name not provided, try to look it up (though usually passed in)
            if not feed_name:
                logger.info(f"Feed name not provided, looking it up")
                all_feeds = self.config_manager.get_feeds()
                logger.info(f"All feeds: {all_feeds}")
                for f in all_feeds:
                    if f["url"] == feed_url:
                        feed_name = f["name"]
                        break
                logger.info(f"Feed name: {feed_name}")
        
        logger.info(f"Polling feed: {feed_name}")
        jobs_found = 0
        skipped_entries = 0
        
        try:
            loop = asyncio.get_event_loop()
            logger.info(f"Polling feed: {real_feed_url}")
            parsed_feed = await loop.run_in_executor(None, feedparser.parse, real_feed_url)
            logger.info(f"Parsed feed: {parsed_feed}")
            if parsed_feed.get("bozo"):
                return {
                    "status": "warning",
                    "message": f"Feed parsed with warnings: {parsed_feed.bozo_exception}",
                    "feed": feed_url,
                    "jobs_found": 0
                }
            
            # Check if this feed needs LLM-based extraction
            use_llm = needs_llm_extraction(feed_url)
            
            # Try to extract company name from feed title or URL
            feed_title = parsed_feed.feed.get("title", "")
            company_name = extract_company_from_feed(feed_url, feed_title)
            logger.info(f"Feed title: {feed_title}")
            logger.info(f"Company name: {company_name}")
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
                        skipped_entries += 1
                        continue
                    
                    # Use extracted metadata
                    job_title = extraction.get("job_title") or entry.get("title", "Unknown Title")
                    entry_company = extraction.get("company_name") or company_name
                else:
                    job_link = original_link
                    job_title = entry.get("title", "Unknown Title")
                    entry_company = entry.get("author") or entry.get("dc_creator") or company_name
                
                if self.deduplicator.is_new(job_link):
                    await self.event_publisher.publish("new_job_ingested", {
                        "job_link": job_link,
                        "title": job_title,
                        "feed_url": feed_url,
                        "feed_name": feed_name,
                        "company_name": entry_company
                    })
                    self.deduplicator.mark_seen(job_link)
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
            logger.error(f"Error polling feed {feed_url}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "feed": feed_url,
                "jobs_found": 0
            }
