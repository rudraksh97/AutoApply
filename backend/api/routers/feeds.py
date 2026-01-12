from fastapi import APIRouter, Depends, HTTPException
from api.services.domain_services import FeedService
from api.dependencies import get_feed_service
from api.schemas.models import FeedURL

from src.rss_watcher import RSSWatcher
from src.infrastructure import JobManagerEventPublisher, JobManagerDeduplicator
from src.job_manager import JobManager
from src.config import ConfigManager

router = APIRouter(prefix="/feeds", tags=["Feeds"])

@router.get("/")
def get_feeds(service: FeedService = Depends(get_feed_service)):
    return service.get_feeds()

@router.post("/")
def add_feed(feed: FeedURL, service: FeedService = Depends(get_feed_service)):
    if service.add_feed(feed.url):
        return {"status": "added", "url": feed.url}
    raise HTTPException(status_code=400, detail="Feed already exists")

@router.delete("/")
def remove_feed(feed: FeedURL, service: FeedService = Depends(get_feed_service)):
    service.remove_feed(feed.url)
    return {"status": "removed", "url": feed.url}

# Test feed URL pattern to skip during "Poll All"
TEST_FEED_PATTERN = "/test/feed.xml"

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
    
    all_feeds = config_manager.get_feeds()
    # Filter out test feeds
    feeds_to_poll = [f for f in all_feeds if TEST_FEED_PATTERN not in f]
    skipped_feeds = [f for f in all_feeds if TEST_FEED_PATTERN in f]
    
    if not feeds_to_poll:
        return {
            "status": "no_feeds", 
            "message": "No real RSS feeds configured (test feeds are skipped)", 
            "jobs_found": 0,
            "skipped": skipped_feeds
        }
    
    # Poll each feed manually (instead of using watcher.poll_once which polls all)
    jobs_found = 0
    for feed_url in feeds_to_poll:
        try:
            loop = asyncio.get_event_loop()
            parsed_feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
            
            for entry in parsed_feed.entries:
                job_link = entry.get("link")
                if not job_link:
                    continue
                
                if deduplicator.is_new(job_link):
                    await event_publisher.publish("new_job_ingested", {
                        "job_link": job_link,
                        "title": entry.get("title", "Unknown Title"),
                        "feed_url": feed_url
                    })
                    deduplicator.mark_seen(job_link)
                    jobs_found += 1
        except Exception as e:
            print(f"Error polling feed {feed_url}: {e}")
    
    return {
        "status": "success",
        "message": f"Polled {len(feeds_to_poll)} feed(s), found {jobs_found} new job(s)",
        "feeds_polled": feeds_to_poll,
        "skipped": skipped_feeds
    }

@router.post("/poll-single")
async def poll_single_feed(feed: FeedURL):
    """
    Manually trigger an immediate poll of a single RSS feed.
    """
    import feedparser
    import asyncio
    
    job_manager = JobManager()
    event_publisher = JobManagerEventPublisher(job_manager)
    deduplicator = JobManagerDeduplicator(job_manager)
    
    feed_url = feed.url
    jobs_found = 0
    
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
        
        for entry in parsed_feed.entries:
            job_link = entry.get("link")
            if not job_link:
                continue
            
            if deduplicator.is_new(job_link):
                await event_publisher.publish("new_job_ingested", {
                    "job_link": job_link,
                    "title": entry.get("title", "Unknown Title"),
                    "feed_url": feed_url
                })
                deduplicator.mark_seen(job_link)
                jobs_found += 1
        
        return {
            "status": "success",
            "message": f"Found {jobs_found} new job(s)",
            "feed": feed_url,
            "jobs_found": jobs_found
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to poll feed: {str(e)}")
