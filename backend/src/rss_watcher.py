from src.job_manager import JobManager
import feedparser

class RSSWatcher:
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager
        self.feeds = [] # Injected by config

    def get_new_jobs(self):
        """Yields new job links from RSS feeds that haven't been seen."""
        if not self.feeds:
            # We print here but in the UI loop it might be noisy; handled by UI logic mostly
            return

        for feed_url in self.feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    job_link = entry.link
                    # Check if exists in JobManager
                    if not self.job_manager.job_exists(job_link):
                        # Add immediately as Pending to prevent double processing if loop is fast
                        self.job_manager.add_job(job_link, status="Pending")
                        yield job_link
            except Exception as e:
                print(f"Error parsing feed {feed_url}: {e}")


if __name__ == "__main__":
    watcher = RSSWatcher()
    # watcher.feeds = ["https://remotive.com/remote-jobs/software-dev/feed"]
    # for job in watcher.get_new_jobs():
    #     print("New job:", job)
