"""
Example consumer for the refactored RSSWatcher.
This demonstrates how downstream processing is decoupled via events.
"""

import asyncio
import logging
from src.rss_watcher import RSSWatcher
from src.infrastructure import InMemoryDeduplicator, AsyncCallbackPublisher

# Mocking the job processing that used to be inline
async def handle_new_job_event(event_type: str, data: dict):
    """
    This is where the heavy lifting happens. 
    It runs in the background, non-blocking for the watcher.
    """
    if event_type == "new_job_ingested":
        job_link = data["job_link"]
        logging.info(f"CONSUMER: Received new job event for {job_link}")
        
        # Simulate heavy processing (scraping, LLM, etc.)
        await asyncio.sleep(2) 
        logging.info(f"CONSUMER: Finished processing job: {job_link}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # 1. Setup Infrastructure
    deduplicator = InMemoryDeduplicator()
    # Using AsyncCallbackPublisher to bridge events to our handler
    publisher = AsyncCallbackPublisher(handle_new_job_event)
    
    # 2. Setup Watcher
    watcher = RSSWatcher(
        event_publisher=publisher,
        deduplicator=deduplicator,
        feeds=["https://news.ycombinator.com/rss"]
    )
    
    # 3. Start Polling (Non-blocking)
    logging.info("Starting example poll...")
    await watcher.poll_once()
    
    # Wait a bit for the background tasks (consumers) to finish
    await asyncio.sleep(5)
    logging.info("Example run complete.")

if __name__ == "__main__":
    asyncio.run(main())
