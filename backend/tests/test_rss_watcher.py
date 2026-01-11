"""
Unit tests for RSSWatcher.

Uses mocked feedparser to avoid network dependencies.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestRSSWatcher:
    """Unit tests for RSS feed parsing and job detection."""
    
    @pytest.fixture
    def mock_job_manager(self):
        """Create a mock JobManager."""
        manager = Mock()
        manager.job_exists = Mock(return_value=False)
        manager.add_job = Mock(return_value=True)
        return manager
    
    @pytest.fixture
    def rss_watcher(self, mock_job_manager):
        """Create an RSSWatcher with mock dependencies."""
        from src.rss_watcher import RSSWatcher
        watcher = RSSWatcher(mock_job_manager)
        return watcher
    
    def test_no_jobs_when_no_feeds(self, rss_watcher):
        """Test that no jobs are found when feeds list is empty."""
        rss_watcher.feeds = []
        
        jobs = list(rss_watcher.get_new_jobs())
        
        assert len(jobs) == 0
    
    @patch('src.rss_watcher.feedparser')
    def test_find_new_jobs_from_feed(self, mock_feedparser, rss_watcher, mock_job_manager):
        """Test finding new jobs from RSS feed."""
        # Setup mock feed response
        mock_entry1 = MagicMock()
        mock_entry1.link = "https://jobs.example.com/job1"
        mock_entry2 = MagicMock()
        mock_entry2.link = "https://jobs.example.com/job2"
        
        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry1, mock_entry2]
        mock_feedparser.parse.return_value = mock_feed
        
        rss_watcher.feeds = ["https://example.com/rss"]
        
        jobs = list(rss_watcher.get_new_jobs())
        
        assert len(jobs) == 2
        assert "https://jobs.example.com/job1" in jobs
        assert "https://jobs.example.com/job2" in jobs
        assert mock_job_manager.add_job.call_count == 2
    
    @patch('src.rss_watcher.feedparser')
    def test_skip_existing_jobs(self, mock_feedparser, rss_watcher, mock_job_manager):
        """Test that existing jobs are skipped."""
        mock_entry = MagicMock()
        mock_entry.link = "https://jobs.example.com/existing"
        
        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        mock_feedparser.parse.return_value = mock_feed
        
        # Mark job as already existing
        mock_job_manager.job_exists.return_value = True
        
        rss_watcher.feeds = ["https://example.com/rss"]
        
        jobs = list(rss_watcher.get_new_jobs())
        
        assert len(jobs) == 0
        mock_job_manager.add_job.assert_not_called()
    
    @patch('src.rss_watcher.feedparser')
    def test_multiple_feeds(self, mock_feedparser, rss_watcher, mock_job_manager):
        """Test processing multiple feeds."""
        mock_entry1 = MagicMock()
        mock_entry1.link = "https://jobs.example.com/from_feed1"
        mock_entry2 = MagicMock()
        mock_entry2.link = "https://jobs.example.com/from_feed2"
        
        mock_feed1 = MagicMock()
        mock_feed1.entries = [mock_entry1]
        mock_feed2 = MagicMock()
        mock_feed2.entries = [mock_entry2]
        
        mock_feedparser.parse.side_effect = [mock_feed1, mock_feed2]
        
        rss_watcher.feeds = ["https://feed1.com/rss", "https://feed2.com/rss"]
        
        jobs = list(rss_watcher.get_new_jobs())
        
        assert len(jobs) == 2
        assert mock_feedparser.parse.call_count == 2
    
    @patch('src.rss_watcher.feedparser')
    def test_handle_feed_parse_error(self, mock_feedparser, rss_watcher, mock_job_manager, capsys):
        """Test graceful handling of feed parse errors."""
        mock_feedparser.parse.side_effect = Exception("Network error")
        
        rss_watcher.feeds = ["https://broken-feed.com/rss"]
        
        # Should not raise, should handle gracefully
        jobs = list(rss_watcher.get_new_jobs())
        
        assert len(jobs) == 0
        captured = capsys.readouterr()
        assert "Error parsing feed" in captured.out
    
    @patch('src.rss_watcher.feedparser')
    def test_empty_feed(self, mock_feedparser, rss_watcher, mock_job_manager):
        """Test handling an empty feed."""
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feedparser.parse.return_value = mock_feed
        
        rss_watcher.feeds = ["https://empty-feed.com/rss"]
        
        jobs = list(rss_watcher.get_new_jobs())
        
        assert len(jobs) == 0
        mock_job_manager.add_job.assert_not_called()
    
    @patch('src.rss_watcher.feedparser')
    def test_mixed_new_and_existing_jobs(self, mock_feedparser, rss_watcher, mock_job_manager):
        """Test feed with mix of new and existing jobs."""
        mock_entry_new = MagicMock()
        mock_entry_new.link = "https://jobs.example.com/new"
        mock_entry_existing = MagicMock()
        mock_entry_existing.link = "https://jobs.example.com/existing"
        
        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry_new, mock_entry_existing]
        mock_feedparser.parse.return_value = mock_feed
        
        # First job is new, second exists
        mock_job_manager.job_exists.side_effect = [False, True]
        
        rss_watcher.feeds = ["https://example.com/rss"]
        
        jobs = list(rss_watcher.get_new_jobs())
        
        assert len(jobs) == 1
        assert "https://jobs.example.com/new" in jobs
        assert mock_job_manager.add_job.call_count == 1
