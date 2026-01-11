from fastapi import APIRouter, Depends, HTTPException
from api.services.domain_services import FeedService
from api.dependencies import get_feed_service
from api.schemas.models import FeedURL

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
