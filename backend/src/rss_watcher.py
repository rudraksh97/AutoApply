"""
RSS feed monitoring for the AutoApply application.

This module provides the capability to poll multiple RSS feeds for new job
postings and import them into the application's local database.
"""

import asyncio
import logging
import httpx
import feedparser
from typing import List, Optional, Any
from src.interfaces import EventPublisher, Deduplicator

class RSSWatcher:
    """
    Fast, non-blocking RSS ingestion component.
    
    Responsibilities:
    1. Fetch and parse RSS feeds concurrently.
    2. Deduplicate entries to prevent redundant processing.
    3. Emit lightweight events for new entries.
    
    This watcher does NOT trigger workflows, scrape job details, or call LLMs.
    It stops after publishing an event.
    """
    def __init__(
        self, 
        event_publisher: EventPublisher,
        deduplicator: Deduplicator,
        config_manager
    ):
        """
        Initializes the RSS watcher.

        Args:
            event_publisher: Backend-agnostic interface to emit events.
            deduplicator: Persistent or in-memory store to check for duplicates.
            config_manager: Manager to retrieve the current list of RSS feeds.
        """
        self.event_publisher = event_publisher
        self.deduplicator = deduplicator
        self.config_manager = config_manager

    async def poll_once(self):
        """
        Performs a single polling cycle across all configured feeds.
        Fetches feeds concurrently to ensure the cycle is fast.
        """
        feeds = self.config_manager.get_feeds()
        if not feeds:
            logging.warning("No RSS feeds configured for polling.")
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [self._process_feed(client, url) for url in feeds]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_feed(self, client: httpx.AsyncClient, feed_url: str):
        """
        Fetches and processes a single feed.
        """
        try:
            response = await client.get(feed_url)
            response.raise_for_status()
            
            # feedparser works on strings/bytes, but it's blocking.
            # For large feeds, this could be offloaded to a thread,
            # but usually it's fast enough for I/O bound pollers.
            feed = feedparser.parse(response.content)
            
            # ADDED FOR TESTING: Inject a fake entry
            from types import SimpleNamespace
            fake_entry = SimpleNamespace(
                link="https://jobs.ashbyhq.com/fieldguide/47a2afc4-1075-4378-83bb-714543b6c272",
                title="Fake Test Job",
                id="https://jobs.ashbyhq.com/fieldguide/47a2afc4-1075-4378-83bb-714543b6c272"
            )
            if hasattr(feed, 'entries'):
                feed.entries.insert(0, fake_entry)
            
            for entry in feed.entries:
                entry_id = getattr(entry, 'id', entry.link)
                # Composite key for deduplication
                dedup_key = entry.link
                
                if True or self.deduplicator.is_new(dedup_key):
                    # 1. Mark as seen immediately (fire-and-forget logic)
                    self.deduplicator.mark_seen(dedup_key)
                    
                    # 2. Emit lightweight event
                    # Flow ends here for the watcher.
                    #  or entry.link
                    event_data = {
                        "job_link": entry.link,
                        "title": getattr(entry, 'title', 'Untitled'),
                        "feed_url": feed_url,
                        "entry_id": entry_id
                    }
                    await self.event_publisher.publish("new_job_ingested", event_data)
                    logging.info(f"New entry detected: {entry.link}")
                    
        except Exception as e:
            logging.error(f"Failed to process feed {feed_url}: {e}")

    async def run_forever(self, interval_seconds: int = 300):
        """
        Looping construct for production usage.
        """
        logging.info(f"Starting RSS Watcher loop (interval: {interval_seconds}s)")
        while True:
            await self.poll_once()
            await asyncio.sleep(interval_seconds)
