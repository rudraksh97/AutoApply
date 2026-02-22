import asyncio
import logging
import os
import signal
import sys
import time
from typing import NoReturn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("RSSPoller")

# Ensure src can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.db import engine, Base
from src.models import User, Profile, Resume, Job, Feed, Settings  # noqa: F401
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")
except Exception as e:
    logger.warning(f"Could not create tables (DB may not be ready): {e}")

from src.services.feed_poll_service import FeedPollService

async def main_loop() -> NoReturn:
    """
    Main polling loop for the RSS microservice.
    """
    logger.info("Starting RSS Poller Microservice...")
    
    service = FeedPollService()
    
    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
        
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    while not stop_event.is_set():
        try:
            logger.info("Triggering RSS poll...")
            start_time = time.time()
            
            result = await service.poll_all_feeds()
            
            elapsed = time.time() - start_time
            logger.info(f"Poll completed in {elapsed:.2f}s: {result.get('message')}")
            
        except Exception as e:
            logger.error(f"Error in polling loop: {e}", exc_info=True)
            
        # Wait for next interval or shutdown signal
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            continue
            
    logger.info("RSS Poller shutting down.")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
             # Windows doesn't support add_signal_handler in the same way for the event loop
             # Use a simpler loop for Windows dev
             
             async def windows_loop():
                 logger.info("Starting RSS Poller (Windows Mode)...")
                 service = FeedPollService()
                 while True:
                     try:
                         logger.info("Triggering RSS poll...")
                         await service.poll_all_feeds()
                     except Exception as e:
                         logger.error(f"Error: {e}")
                     await asyncio.sleep(30)
                     
             asyncio.run(windows_loop())
        else:
            asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
