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
from src.config import ConfigManager
from src.services.feed_poll_service import FeedPollService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feeds", tags=["Feeds"])



@router.get("/status")
def get_polling_status():
    """Get the current status of the background feed poller."""
    service = FeedPollService()
    # Since stats are static/class-level, we can just call the static method or instance method
    return service.get_status()

@router.get("")
def get_feeds(service: FeedService = Depends(get_feed_service)):
    return service.get_feeds()

@router.post("")
def add_feed(feed: FeedURL, service: FeedService = Depends(get_feed_service)):
    if service.add_feed(feed.url, feed.name):
        return {"status": "added", "url": feed.url, "name": feed.name}
    raise HTTPException(status_code=400, detail="Feed URL or name already exists")

@router.delete("")
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
    service = FeedPollService()
    return await service.poll_all_feeds()

@router.post("/poll-single")
async def poll_single_feed(feed: FeedURLOnly):
    """
    Manually trigger an immediate poll of a single RSS feed.
    """
    service = FeedPollService()
    result = await service.poll_feed(feed.url)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=f"Failed to poll feed: {result.get('message')}")
        
    return result
