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
from src.db import SessionLocal
from src.models import Feed, User
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
        # self.config_manager = ConfigManager() # Removed
        self.event_publisher = JobManagerEventPublisher(self.job_manager)
        self.deduplicator = JobManagerDeduplicator(self.job_manager)

    async def poll_all_feeds(self) -> Dict[str, Any]:
        """
        Polls all configured RSS feeds (skipping test feeds) for new jobs.
        """
        FeedPollService._is_polling = True
        db = SessionLocal()
        try:
            # 1. Fetch all feeds
            all_feeds_db = db.query(Feed).all()
            
            # 2. Fetch all users and their settings to determine global opt-in
            users = db.query(User).all()
            user_settings_map = {}
            for u in users:
                # Default include_global = True if no settings row
                if u.settings:
                    user_settings_map[u.id] = u.settings.include_global_feeds
                else:
                    user_settings_map[u.id] = True

            # 3. Group users by Feed URL
            # Map: feed_url -> { "name": str, "target_users": Set[str], "is_global": bool }
            feed_map = {}

            for f in all_feeds_db:
                if TEST_FEED_PATTERN in f.url:
                    continue
                
                if f.url not in feed_map:
                    feed_map[f.url] = {
                        "name": f.name,
                        "target_users": set(),
                        "is_global": False
                    }
                
                # Update metadata
                # If any entry is global, mark URL as global source
                if f.is_global:
                    feed_map[f.url]["is_global"] = True
                
                # Add owner to target
                feed_map[f.url]["target_users"].add(f.user_id)

            # 4. Add Global subscribers
            # For every feed that is global, add ALL users who opted in (excluding those who already have it private to avoid double count, strictly set ensures uniqueness)
            for url, data in feed_map.items():
                if data["is_global"]:
                    for u in users:
                        if user_settings_map.get(u.id, True):
                            data["target_users"].add(u.id)

            feeds_to_poll = list(feed_map.items())
            logger.info(f"Feeds to poll: {[u for u, _ in feeds_to_poll]}")
            
            if not feeds_to_poll:
                 return {
                    "status": "no_feeds", 
                    "message": "No feeds configured.", 
                    "jobs_found": 0
                }

            jobs_found = 0
            feeds_polled = []
            
            for url, data in feeds_to_poll:
                logger.info(f"Polling feed: {url} for users: {len(data['target_users'])}")
                result = await self.poll_feed(url, data["name"], list(data["target_users"]))
                if result.get("status") == "success":
                    jobs_found += result.get("jobs_found", 0)
                    feeds_polled.append(url)
                else:
                    logger.warning(f"Failed to poll {url}: {result.get('message')}")

            # Update stats (write to DB)
            FeedPollService._last_poll_time = time.time()
            FeedPollService._total_polls += 1
            FeedPollService._last_jobs_found = jobs_found
            logger.info(f"Jobs found: {jobs_found}")
            FeedPollService._save_status_to_db()

            return {
                "status": "success",
                "message": f"Polled {len(feeds_to_poll)} unique feed(s), found {jobs_found} new job(s)",
                "feeds_polled": feeds_polled,
                "jobs_found": jobs_found
            }
            
        finally:
            db.close()
            FeedPollService._is_polling = False
            FeedPollService._save_status_to_db()

    @classmethod
    def _save_status_to_db(cls):
        """Writes current poller status to the SystemState DB. Non-fatal on error."""
        from datetime import datetime
        status_data = {
            "last_poll_time": cls._last_poll_time,
            "total_polls": cls._total_polls,
            "last_jobs_found": cls._last_jobs_found,
            "is_polling": cls._is_polling,
        }
        try:
            db = SessionLocal()
            try:
                from src.models import SystemState
                row = db.query(SystemState).filter(SystemState.key == "poller_status").first()
                if row:
                    row.value = status_data
                    row.updated_at = datetime.utcnow()
                else:
                    db.add(SystemState(key="poller_status", value=status_data))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to write poller status to DB: {e}")

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Get the current poller status from the SystemState DB."""
        try:
            db = SessionLocal()
            try:
                from src.models import SystemState
                row = db.query(SystemState).filter(SystemState.key == "poller_status").first()
                return row.value if row and row.value else {
                    "last_poll_time": 0, "total_polls": 0,
                    "last_jobs_found": 0, "is_polling": False
                }
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to read poller status from DB: {e}")
            return {"last_poll_time": 0, "total_polls": 0, "last_jobs_found": 0, "is_polling": False}

    async def poll_feed_by_url(self, feed_url: str) -> Dict[str, Any]:
        """
        Helper to poll a single feed by URL, resolving target users from DB.
        """
        FeedPollService._is_polling = True
        db = SessionLocal()
        try:
            # 1. Check if feed exists and get properties
            # There could be multiple entries for same URL (private feeds)
            # and potentially global flag.
            feeds = db.query(Feed).filter(Feed.url == feed_url).all()
            if not feeds:
                 return {"status": "error", "message": "Feed not found in database", "feed": feed_url}
            
            # 2. Resolve Users
            users = db.query(User).all()
            user_settings_map = {u.id: (u.settings.include_global_feeds if u.settings else True) for u in users}
            
            target_user_ids = set()
            feed_name = feeds[0].name # Pick first name
            is_global = False

            for f in feeds:
                target_user_ids.add(f.user_id)
                if f.is_global:
                    is_global = True
                    # Use name from global def if available?
                    if f.name: feed_name = f.name
            
            if is_global:
                for u in users:
                    if user_settings_map.get(u.id, True):
                        target_user_ids.add(u.id)
            
            return await self.poll_feed(feed_url, feed_name, list(target_user_ids))
        finally:
             db.close()
             FeedPollService._is_polling = False
             FeedPollService._save_status_to_db()
             
    async def poll_feed(self, feed_url: str, feed_name: str = None, target_user_ids: List[str] = []) -> Dict[str, Any]:
    # ... rest of poll_feed ...
        if TEST_FEED_PATTERN in feed_url:
            logger.info(f"Polling test feed: {feed_url}")
            feed_name = "Test" if not feed_name else feed_name
            # Fix: Map relative frontend URL to absolute backend URL for feedparser
            real_feed_url = "http://localhost:8000/test/feed.xml"
        else:
            real_feed_url = feed_url
            # logger.info(f"Polling feed: {real_feed_url}")
        
        jobs_found = 0
        skipped_entries = 0
        
        try:
            loop = asyncio.get_event_loop()
            parsed_feed = await loop.run_in_executor(None, feedparser.parse, real_feed_url)
            
            if parsed_feed.get("bozo"):
                 # Log warning but try to proceed? 
                 # Often bozo=1 is just encoding issue but content is parsable.
                 logger.warning(f"Feed {feed_url} parsed with warnings: {parsed_feed.bozo_exception}")

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
                    # Attribution: use the first target user as the "payer" or global if none
                    attribution_id = target_user_ids[0] if target_user_ids else None
                    extraction = await extract_job_link_with_llm(entry, user_id=attribution_id)
                    job_link = extraction.get("job_url")
                    
                    if not job_link:
                        skipped_entries += 1
                        continue
                    
                    job_title = extraction.get("job_title") or entry.get("title", "Unknown Title")
                    entry_company = extraction.get("company_name") or company_name
                else:
                    job_link = original_link
                    job_title = entry.get("title", "Unknown Title")
                    entry_company = entry.get("author") or entry.get("dc_creator") or company_name
                
                # Distribute to target users
                for uid in target_user_ids:
                    if self.deduplicator.is_new(job_link, user_id=uid):
                        await self.event_publisher.publish("new_job_ingested", {
                            "job_link": job_link,
                            "title": job_title,
                            "feed_url": feed_url,
                            "feed_name": feed_name,
                            "company_name": entry_company,
                            "user_id": uid
                        })
                        # self.deduplicator.mark_seen(job_link, user_id=uid) # Handled by add_job
                        jobs_found += 1
            
            return {
                "status": "success",
                "message": f"Found {jobs_found} new job(s) across {len(target_user_ids)} users",
                "feed": feed_url,
                "jobs_found": jobs_found,  # This might be total NEW assignments (job * users)
                "llm_extraction": use_llm
            }
            
        except Exception as e:
            logger.error(f"Error polling feed {feed_url}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "feed": feed_url,
                "jobs_found": 0
            }
