"""
Unit tests for RSSWatcher.

Uses mocked feedparser to avoid network dependencies.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.rss_watcher import RSSWatcher
from src.infrastructure import InMemoryDeduplicator

class TestRSSWatcher:
    """Unit tests for the refactored, async RSSWatcher."""

    @pytest.fixture
    def mock_publisher(self):
        """Create a mock EventPublisher."""
        return AsyncMock()

    @pytest.fixture
    def deduplicator(self):
        """Use InMemoryDeduplicator for unit testing."""
        return InMemoryDeduplicator()

    @pytest.fixture
    def rss_watcher(self, mock_publisher, deduplicator):
        """Create an RSSWatcher with mock dependencies."""
        return RSSWatcher(
            event_publisher=mock_publisher,
            deduplicator=deduplicator
        )

    @pytest.mark.asyncio
    async def test_no_polling_when_no_feeds(self, rss_watcher, mock_publisher):
        """Test that nothing happens when feeds list is empty."""
        rss_watcher.feeds = []
        await rss_watcher.poll_once()
        mock_publisher.publish.assert_not_called()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_detect_and_publish_new_jobs(self, mock_get, rss_watcher, mock_publisher):
        """Test detecting new jobs and emitting events."""
        # Setup mock RSS response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"""<?xml version="1.0" encoding="UTF-8" ?>
        <rss version="2.0">
        <channel>
          <item>
            <title>Job 1</title>
            <link>https://example.com/job1</link>
            <guid>1</guid>
          </item>
          <item>
            <title>Job 2</title>
            <link>https://example.com/job2</link>
            <guid>2</guid>
          </item>
        </channel>
        </rss>"""
        mock_get.return_value = mock_response

        rss_watcher.feeds = ["https://example.com/rss"]
        await rss_watcher.poll_once()

        # Verify events were published
        assert mock_publisher.publish.call_count == 2
        
        # Verify call arguments for first job
        args, kwargs = mock_publisher.publish.call_args_list[0]
        assert args[0] == "new_job_ingested"
        assert args[1]["job_link"] == "https://example.com/job1"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_deduplication(self, mock_get, rss_watcher, mock_publisher):
        """Test that duplicate entries are not re-published."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"""<?xml version="1.0" encoding="UTF-8" ?>
        <rss version="2.0">
        <channel>
          <item>
            <link>https://example.com/job1</link>
            <guid>1</guid>
          </item>
        </channel>
        </rss>"""
        mock_get.return_value = mock_response

        rss_watcher.feeds = ["https://example.com/rss"]
        
        # First poll
        await rss_watcher.poll_once()
        assert mock_publisher.publish.call_count == 1
        
        # Second poll - same content
        await rss_watcher.poll_once()
        assert mock_publisher.publish.call_count == 1 # Still 1

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_handle_network_error(self, mock_get, rss_watcher, mock_publisher):
        """Test graceful handling of network errors."""
        mock_get.side_effect = httpx.ConnectError("Connection failed")
        
        rss_watcher.feeds = ["https://broken.com/rss"]
        
        # Should NOT raise an exception
        await rss_watcher.poll_once()
        mock_publisher.publish.assert_not_called()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_multiple_feeds_concurrency(self, mock_get, rss_watcher, mock_publisher):
        """Test that multiple feeds are polled."""
        # Return different content for each feed to ensure unique links
        def side_effect(url):
            resp = MagicMock()
            resp.status_code = 200
            resp.content = f"""<?xml version="1.0" encoding="UTF-8" ?><rss version="2.0"><channel><item><link>https://x.com/{url}</link></item></channel></rss>""".encode('utf-8')
            return resp
        
        mock_get.side_effect = side_effect

        rss_watcher.feeds = ["https://f1.com", "https://f2.com", "https://f3.com"]
        
        await rss_watcher.poll_once()
        
        assert mock_get.call_count == 3
        assert mock_publisher.publish.call_count == 3
