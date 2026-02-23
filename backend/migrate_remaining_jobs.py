import sqlite3
import os
import sys
from datetime import datetime
from sqlalchemy.orm import Session

# Add current directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.db import SessionLocal
from src.models import Job, User, Feed

# Configuration
SQLITE_DB = "../jobs.db"
USER_MAP = {
    "shubham": "4a1e4b7e-6569-4942-a71d-36d4db18d82b", # shubhamjainn1256
    "devhax": "71c6ea1d-e07e-4c77-a580-ca0c0330ed55"   # devhaxcodes
}

DEVHAX_FEED_ID_PREFIX = "16255412850507629906"

def migrate():
    if not os.path.exists(SQLITE_DB):
        print(f"Error: {SQLITE_DB} not found.")
        return

    # 1. Connect to databases
    sq_conn = sqlite3.connect(SQLITE_DB)
    sq_cursor = sq_conn.cursor()
    
    pg_db = SessionLocal()
    
    try:
        # 2. Pre-fetch Supabase data for mapping
        print("Fetching feeds from Supabase...")
        feeds_db = pg_db.query(Feed).all()
        feed_url_to_id = {f.url: f.id for f in feeds_db}
        print(f"Loaded {len(feed_url_to_id)} feeds from Supabase.")

        # 3. Fetch jobs from SQLite
        print("Fetching jobs from SQLite...")
        sq_cursor.execute("SELECT * FROM jobs")
        sqlite_jobs = sq_cursor.fetchall()
        
        # Get column names
        sq_cursor.execute("PRAGMA table_info(jobs)")
        cols = [col[1] for col in sq_cursor.fetchall()]
        print(f"Found {len(sqlite_jobs)} jobs in SQLite.")

        inserted_count = 0
        skipped_count = 0
        error_count = 0

        # 4. Process each job
        for row in sqlite_jobs:
            job_data = dict(zip(cols, row))
            url = job_data['url']
            source_feed_url = job_data['source_feed']
            
            # Determine target user
            if source_feed_url and DEVHAX_FEED_ID_PREFIX in source_feed_url:
                target_user_id = USER_MAP["devhax"]
            else:
                target_user_id = USER_MAP["shubham"]
            
            # Find matching feed in Supabase
            feed_id = feed_url_to_id.get(source_feed_url)
            
            # Check if job already exists in PG
            existing = pg_db.query(Job).filter(Job.url == url, Job.user_id == target_user_id).first()
            if existing:
                skipped_count += 1
                continue
            
            try:
                # Map SQLite status to PG status (limited to model choices)
                status = job_data['status']
                if status == "Draft Failed":
                    status = "FAILED"
                elif status not in ["APPLIED", "PENDING", "FAILED", "RETRIED"]:
                    status = "PENDING"

                # Parse created_at
                created_at = datetime.utcnow()
                if job_data['timestamp']:
                    try:
                        created_at = datetime.strptime(job_data['timestamp'], '%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                new_job = Job(
                    url=url,
                    user_id=target_user_id,
                    feed_id=feed_id,
                    role=job_data.get('job_title', 'Unknown Role'),
                    status=status,
                    created_at=created_at,
                    pdf_path=job_data.get('pdf_path'),
                    details=job_data.get('details'),
                    error_message=job_data.get('error_message'),
                    sent=bool(job_data.get('sent', 0)),
                    retry_count=job_data.get('retry_count', 0),
                    apply_link=job_data.get('apply_link')
                )
                
                pg_db.add(new_job)
                inserted_count += 1
                
                # Commit every 50 records to avoid huge transactions
                if inserted_count % 50 == 0:
                    pg_db.commit()
                    print(f"Inserted {inserted_count} jobs...")
                    
            except Exception as e:
                print(f"Error inserting job {url}: {e}")
                error_count += 1
                pg_db.rollback()

        pg_db.commit()
        print("\n--- Migration Complete ---")
        print(f"Total jobs in SQLite: {len(sqlite_jobs)}")
        print(f"Successfully inserted: {inserted_count}")
        print(f"Skipped (already exists): {skipped_count}")
        print(f"Errors encountered: {error_count}")
        
    finally:
        pg_db.close()
        sq_conn.close()

if __name__ == "__main__":
    migrate()
