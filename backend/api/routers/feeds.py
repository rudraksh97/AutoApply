from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from src.db import get_db
from src.models import Feed, User, Settings
from src.services.feed_poll_service import FeedPollService
from api.dependencies import get_current_user
from api.schemas.models import FeedURL, FeedURLOnly
from pydantic import BaseModel

class FeedCreate(FeedURL):
    is_global: bool = False

class FeedResponse(FeedURL):
    id: str
    is_global: bool
    user_id: str
    class Config:
        from_attributes = True

router = APIRouter(prefix="/feeds", tags=["Feeds"])

@router.get("", response_model=List[FeedResponse])
def get_feeds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get user settings
    user_settings = db.query(Settings).filter(Settings.user_id == current_user.id).first()
    include_global = True
    if user_settings:
        include_global = user_settings.include_global_feeds
    
    # Base query: My feeds
    query = db.query(Feed).filter(Feed.user_id == current_user.id)
    
    if include_global:
        # Fetch my feeds OR global feeds
        query = db.query(Feed).filter(
            or_(
                Feed.user_id == current_user.id,
                Feed.is_global == True
            )
        )
    
    return query.all()

@router.post("", response_model=FeedResponse)
def add_feed(
    feed: FeedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only admin can set is_global
    if feed.is_global and "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Only admins can create global feeds")

    # Check existence (URL + User logic or Global logic)
    existing = db.query(Feed).filter(Feed.url == feed.url).first() 
    # If existing is global, and user trying to add private: OK?
    # If existing is private (other user), OK.
    # If existing is private (same user), Error.
    if existing:
        if existing.user_id == current_user.id:
             raise HTTPException(status_code=400, detail="You already have this feed")
        if existing.is_global and feed.is_global:
             raise HTTPException(status_code=400, detail="Global feed with this URL already exists")

    new_feed = Feed(
        url=feed.url,
        name=feed.name,
        is_global=feed.is_global,
        user_id=current_user.id
    )
    db.add(new_feed)
    db.commit()
    db.refresh(new_feed)
    return new_feed

@router.delete("/{feed_id}")
def remove_feed(
    feed_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Support deletion by ID or URL? 
    # Original API used URL in body. But ID is cleaner.
    # I'll stick to ID path param as it's standard REST.
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
        
    # Check permissions
    if feed.user_id != current_user.id:
        # If not owner, check if admin
        if "admin" not in current_user.roles:
            raise HTTPException(status_code=403, detail="Not authorized to delete this feed")
    
    db.delete(feed)
    db.commit()
    return {"status": "removed", "id": feed_id}

@router.delete("")
def remove_feed_by_url(
    feed: FeedURLOnly,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Legacy support
    feed_obj = db.query(Feed).filter(Feed.url == feed.url, Feed.user_id == current_user.id).first()
    if not feed_obj:
         # Try find global if admin
         if "admin" in current_user.roles:
             feed_obj = db.query(Feed).filter(Feed.url == feed.url, Feed.is_global == True).first()
    
    if not feed_obj:
        raise HTTPException(status_code=404, detail="Feed not found")

    db.delete(feed_obj)
    db.commit()
    return {"status": "removed", "url": feed.url}

@router.get("/status")
def get_polling_status(
    db: Session = Depends(get_db)
):
    """
    Returns the current RSS poller status from the SystemState DB.
    This is updated by both the rss-poller container and inline polls.
    """
    from src.models import SystemState
    row = db.query(SystemState).filter(SystemState.key == "poller_status").first()
    if row and row.value:
        return row.value
    return {"last_poll_time": 0, "total_polls": 0, "last_jobs_found": 0, "is_polling": False}

@router.post("/poll")
async def poll_feeds_now(
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an immediate RSS poll in the background.
    Returns immediately with status='polling_started'.
    Use GET /feeds/status to monitor progress.
    """
    import asyncio
    service = FeedPollService()
    asyncio.create_task(service.poll_all_feeds())
    return {"status": "polling_started", "message": "Poll triggered in background. Check /feeds/status for updates."}

@router.post("/poll-single")
async def poll_single_feed(feed: FeedURLOnly, current_user: User = Depends(get_current_user)):
    service = FeedPollService()
    # Use helper that resolves target users from DB
    return await service.poll_feed_by_url(feed.url)
