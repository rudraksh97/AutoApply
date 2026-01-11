
import os
import pytest
import sqlite3
from src.job_manager import JobManager
from src.database import init_db, DB_FILE

# Use a temporary DB for testing
TEST_DB = "data/jobs_test.db"

@pytest.fixture
def job_manager():
    # Setup: Switch DB file to test file (monkeypatching would be better but simple env swap works for now if we mock)
    # Actually, let's just use the real class but ensure we clean up.
    # Since JobManager calls init_db internally which uses global DB_FILE, 
    # we need to be careful.
    
    # For this simple test, we will assume standard DB_FILE but clean it or mock it.
    # To avoid messing with production DB, let's rename it temporarily if it exists.
    
    real_db = "data/jobs.db"
    backup_db = "data/jobs.db.test_backup"
    
    if os.path.exists(real_db):
        os.rename(real_db, backup_db)
        
    # Clear any existing test data
    if os.path.exists(real_db):
        os.remove(real_db) # Should be gone from rename, but just in case
        
    jm = JobManager()
    yield jm
    
    # Teardown
    if os.path.exists(real_db):
        os.remove(real_db)
    if os.path.exists(backup_db):
        os.rename(backup_db, real_db)

def test_add_job(job_manager):
    assert job_manager.add_job("http://example.com/job1", "Pending") == True
    assert job_manager.add_job("http://example.com/job1", "Pending") == False # Duplicate

def test_get_jobs(job_manager):
    job_manager.add_job("http://example.com/job1", "Pending")
    job_manager.add_job("http://example.com/job2", "Applied")
    
    jobs = job_manager.get_all_jobs()
    assert len(jobs) == 2
    # Sort by URL to ensure deterministic test order regardless of timestamp collision
    jobs.sort(key=lambda x: x['url'])
    assert jobs[0]['url'] == "http://example.com/job1"
    assert jobs[1]['url'] == "http://example.com/job2"

def test_update_job(job_manager):
    url = "http://example.com/update_test"
    job_manager.add_job(url, "Pending")
    
    assert job_manager.update_job(url, status="Applied", details="Role: Dev") == True
    
    jobs = job_manager.get_all_jobs()
    job = jobs[0]
    assert job['status'] == "Applied"
    assert job['details'] == "Role: Dev"
    
def test_job_exists(job_manager):
    url = "http://example.com/exists"
    assert job_manager.job_exists(url) == False
    job_manager.add_job(url)
    assert job_manager.job_exists(url) == True
