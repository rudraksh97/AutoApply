from sqlalchemy.orm import Session
from src.db import SessionLocal
from src.models import Job, Feed, User
from src.url_utils import normalize_job_url
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class JobManager:
    """
    Manages job application database using SQLAlchemy.
    """
    def __init__(self):
        # Migrations handled externally
        pass

    def get_all_jobs(self, user_id=None):
        db = SessionLocal()
        try:
            if user_id:
                jobs = db.query(Job).filter(Job.user_id == user_id).order_by(Job.created_at.desc()).all()
            else:
                 # Admin view or legacy
                jobs = db.query(Job).order_by(Job.created_at.desc()).all()
            return [self._to_dict(job) for job in jobs]
        finally:
            db.close()

    def _to_dict(self, job):
        return {
            "url": job.url,
            "status": job.status,
            "role": job.role,
            "feed_id": job.feed_id,
            "timestamp": job.created_at.isoformat() if job.created_at else "",
            "pdf_path": job.pdf_path,
            "details": job.details,
            "error_message": job.error_message,
            "sent": job.sent,
            "retry_count": job.retry_count,
            "apply_link": job.apply_link,
            # Backwards compatibility key?
            "source_feed": job.feed.url if job.feed else None,
            "source_feed_name": job.feed.name if job.feed else None
        }

    def job_exists(self, url, user_id):
        url = normalize_job_url(url)
        db = SessionLocal()
        try:
            return db.query(Job).filter(Job.url == url, Job.user_id == user_id).first() is not None
        finally:
            db.close()

    def add_job(self, url, user_id, status="PENDING", source_feed=None, source_feed_name=None, job_title=None):
        url = normalize_job_url(url)
        if not user_id:
            logger.error("Attempted to add job without user_id")
            return False
            
        db = SessionLocal()
        try:
            # Check exist for this user
            if db.query(Job).filter(Job.url == url, Job.user_id == user_id).first():
                return False

            feed_id = None
            if source_feed:
                 feed = db.query(Feed).filter(Feed.url == source_feed).first()
                 # Note: Ideally we find the feed relevant to the user or global 
                 # but for now linking to ANY feed with that URL is okay for tracking source.
                 if feed:
                     feed_id = feed.id
            
            job = Job(
                url=url,
                status="PENDING",
                feed_id=feed_id,
                user_id=user_id,
                role=job_title or "Unknown Role",
                created_at=datetime.utcnow()
            )
            
            db.add(job)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding job: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def update_job(self, url, user_id, status=None, pdf_path=None, details=None, error_message=None, 
                   source_feed=None, source_feed_name=None, job_title=None, apply_link=None):
        url = normalize_job_url(url)
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.url == url, Job.user_id == user_id).first()
            if not job:
                return False
            
            if status: job.status = status
            if pdf_path: job.pdf_path = pdf_path
            if details: job.details = str(details)
            if error_message is not None: job.error_message = str(error_message) if error_message else None
            if job_title: job.role = job_title
            if apply_link: job.apply_link = apply_link
            
            # Feed update logic?
            if source_feed:
                 feed = db.query(Feed).filter(Feed.url == source_feed).first()
                 if feed:
                     job.feed_id = feed.id
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating job: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def delete_job(self, url, user_id):
        url = normalize_job_url(url)
        from src.draft_manager import DraftManager
        try:
             DraftManager().delete_draft_by_url(url)
        except: pass

        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.url == url, Job.user_id == user_id).first()
            if job:
                db.delete(job)
                db.commit()
                return True
            return False
        finally:
            db.close()

    def mark_as_sent(self, url, sent=True, user_id=None):
        url = normalize_job_url(url)
        db = SessionLocal()
        try:
            if user_id:
                job = db.query(Job).filter(Job.url == url, Job.user_id == user_id).first()
            else:
                # Fallback for worker if user_id unknown?
                # Actually worker should know user_id. 
                # If ambiguous, filter by url only? Dangerous.
                # Assuming worker loop has user_id, making it required is safer.
                job = db.query(Job).filter(Job.url == url).first()

            if job:
                job.sent = sent
                db.commit()
                return True
            return False
        finally:
            db.close()

    def increment_retry_count(self, url, user_id=None):
        url = normalize_job_url(url)
        db = SessionLocal()
        try:
            if user_id:
                job = db.query(Job).filter(Job.url == url, Job.user_id == user_id).first()
            else:
                job = db.query(Job).filter(Job.url == url).first()

            if job:
                job.retry_count = (job.retry_count or 0) + 1
                db.commit()
                return True
            return False
        finally:
            db.close()
