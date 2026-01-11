
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.rss_watcher import RSSWatcher
from src.interfaces import EventPublisher, Deduplicator

class MockConfigManager:
    def __init__(self):
        self.feeds = ["http://feed1.com"]
    def get_feeds(self):
        return self.feeds
    def set_feeds(self, feeds):
        self.feeds = feeds

@pytest.mark.asyncio
async def test_dynamic_feed_loading():
    # Setup mocks
    mock_publisher = MagicMock(spec=EventPublisher)
    mock_publisher.publish = AsyncMock()
    
    mock_deduplicator = MagicMock(spec=Deduplicator)
    mock_deduplicator.is_new = MagicMock(return_value=True)
    mock_deduplicator.mark_seen = MagicMock()
    
    mock_config = MockConfigManager()
    
    watcher = RSSWatcher(
        event_publisher=mock_publisher,
        deduplicator=mock_deduplicator,
        config_manager=mock_config
    )
    
    # Mock httpx client to avoid real network calls
    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = MockClient.return_value.__aenter__.return_value
        mock_client_instance.get = AsyncMock()
        mock_client_instance.get.return_value.status_code = 200
        # Minimal valid RSS to pass feedparser
        mock_client_instance.get.return_value.content = b"""
        <rss version="2.0">
            <channel><title>Test</title><item><link>http://item1.com</link></item></channel>
        </rss>
        """
        
        # 1. First poll with initial feed
        await watcher.poll_once()
        
        # Verify it called for feed1
        assert mock_client_instance.get.call_count == 1
        call_args = mock_client_instance.get.await_args_list[0]
        assert call_args[0][0] == "http://feed1.com"
        
        # 2. Update config dynamically
        mock_config.set_feeds(["http://feed1.com", "http://feed2.com"])
        
        # 3. Second poll should pick up both
        mock_client_instance.get.reset_mock()
        await watcher.poll_once()
        
        assert mock_client_instance.get.call_count == 2
        urls = [call[0][0] for call in mock_client_instance.get.await_args_list]
        assert "http://feed1.com" in urls
        assert "http://feed2.com" in urls
