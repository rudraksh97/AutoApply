"""
RSS feed monitoring for the AutoApply application.

This module provides the capability to poll multiple RSS feeds for new job
postings and import them into the application's local database.
"""

from src.job_manager import JobManager
import feedparser

class RSSWatcher:
    """
    Watches RSS feeds and identifies new job postings.

    It interacts with the JobManager to ensure duplicate postings are not 
    imported and manages the list of target feed URLs.
    """
    def __init__(self, job_manager: JobManager):
        """
        Initializes the RSS watcher.

        Args:
            job_manager: An instance of JobManager to check for existence
                         and save new jobs.
        """
        self.job_manager = job_manager
        self.feeds = [] # Injected by config

    def get_new_jobs(self):
        """
        Polls configured feeds and yields new job links that haven't been seen.

        It parses each feed, extracts URLs from entries, and checks if they
        already exist in the JobManager. New jobs are added to the database
        with a 'Pending' status.

        Yields:
            str: The URL of a newly discovered job.
        """
        if not self.feeds:
            return

        for feed_url in self.feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    job_link = entry.link
                    # Check if exists in JobManager
                    if not self.job_manager.job_exists(job_link):
                        # Add immediately as Pending to prevent double processing
                        self.job_manager.add_job(job_link, status="Pending")
                        yield job_link
            except Exception as e:
                import logging
                logging.error(f"Error parsing feed {feed_url}: {e}")



if __name__ == "__main__":
    watcher = RSSWatcher()
    # watcher.feeds = ["https://remotive.com/remote-jobs/software-dev/feed"]
    # for job in watcher.get_new_jobs():
    #     print("New job:", job)
