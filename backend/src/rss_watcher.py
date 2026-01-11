import feedparser
import asyncio
import logging
from typing import Optional, List
from src.interfaces import EventPublisher, Deduplicator, ConfigManagerProtocol

class RSSWatcher:
    """
    Service responsible for polling RSS feeds and identifying new job listings.
    It uses a Deduplicator to ensure each job is only processed once and an 
    EventPublisher to signal when a new job is found.
    """
    def __init__(
        self, 
        event_publisher: EventPublisher, 
        deduplicator: Deduplicator,
        config_manager: ConfigManagerProtocol
    ):
        self.event_publisher = event_publisher
        self.deduplicator = deduplicator
        self.config_manager = config_manager

    async def poll_once(self):
        """
        Executes a single polling cycle across all configured RSS feeds.
        """
        feeds = self.config_manager.get_feeds()
        if not feeds:
            logging.info("No RSS feeds configured. Skipping poll.")
            return

        for feed_url in feeds:
            try:
                # We offload the blocking feedparser.parse to a thread if needed,
                # but for simple usage, direct is fine or use loop.run_in_executor
                loop = asyncio.get_event_loop()
                feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
                
                if feed.get("bozo"):
                    logging.warning(f"Possible error parsing feed {feed_url}: {feed.bozo_exception}")

                for entry in feed.entries:
                    # Deduplicate based on link or id
                    # We use the link as the key for JobManager compatibility
                    job_link = entry.get("link")
                    if not job_link:
                        continue
                        
                    if self.deduplicator.is_new(job_link):
                        await self.event_publisher.publish("new_job_ingested", {
                            "job_link": job_link,
                            "title": entry.get("title", "Unknown Title"),
                            "feed_url": feed_url
                        })
                        self.deduplicator.mark_seen(job_link)
            except Exception as e:
                logging.error(f"Error polling feed {feed_url}: {e}")
