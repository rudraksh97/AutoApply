"use client";
import { useState } from 'react';
import { Rss, Trash2, RefreshCw, PlayCircle } from 'lucide-react';

interface Feed {
  id: string;
  name: string;
  url: string;
}

export function RssFeedsPage() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [feedName, setFeedName] = useState('');
  const [feedUrl, setFeedUrl] = useState('');
  const [polling, setPolling] = useState<string | null>(null);

  const handleAddFeed = () => {
    if (feedName.trim() && feedUrl.trim()) {
      const newFeed: Feed = {
        id: Date.now().toString(),
        name: feedName,
        url: feedUrl,
      };
      setFeeds([...feeds, newFeed]);
      setFeedName('');
      setFeedUrl('');
    }
  };

  const handleDeleteFeed = (id: string) => {
    setFeeds(feeds.filter(feed => feed.id !== id));
  };

  const handlePollFeed = async (id: string) => {
    setPolling(id);
    // Simulate polling
    await new Promise(resolve => setTimeout(resolve, 1500));
    setPolling(null);
  };

  const handlePollAll = async () => {
    setPolling('all');
    await new Promise(resolve => setTimeout(resolve, 2000));
    setPolling(null);
  };

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-semibold text-[#0C2C55]">RSS Feeds</h1>
          <div className="flex gap-3">
            <button
              onClick={handlePollAll}
              disabled={polling === 'all'}
              className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <PlayCircle className="w-4 h-4" />
              {polling === 'all' ? 'Polling...' : 'Poll All'}
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#E8E2DB]/50 transition-colors">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Add Feed Form */}
        <div className="bg-white rounded-lg border border-[#629FAD]/30 p-6 mb-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#0C2C55] mb-4">Add New Feed</h2>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Feed Name"
              value={feedName}
              onChange={(e) => setFeedName(e.target.value)}
              className="flex-1 px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374] bg-white text-[#0C2C55]"
            />
            <input
              type="url"
              placeholder="Feed URL"
              value={feedUrl}
              onChange={(e) => setFeedUrl(e.target.value)}
              className="flex-1 px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374] bg-white text-[#0C2C55]"
            />
            <button
              onClick={handleAddFeed}
              className="px-6 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
            >
              Add Feed
            </button>
          </div>
        </div>

        {/* Test Feed Card */}
        <div className="bg-[#629FAD]/10 border border-[#629FAD]/30 rounded-lg p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-[#629FAD]/20 rounded-lg">
                <Rss className="w-6 h-6 text-[#296374]" />
              </div>
              <div>
                <h3 className="font-semibold text-[#0C2C55]">Test Feed</h3>
                <p className="text-sm text-[#296374] mt-1">https://example.com/test-feed.xml</p>
                <p className="text-sm text-[#296374] mt-2">This is a permanent test feed for verification</p>
              </div>
            </div>
            <button
              onClick={() => handlePollFeed('test')}
              disabled={polling === 'test'}
              className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 disabled:opacity-50 transition-colors"
            >
              <PlayCircle className="w-4 h-4" />
              {polling === 'test' ? 'Polling...' : 'Poll'}
            </button>
          </div>
        </div>

        {/* Feeds List */}
        {feeds.length === 0 ? (
          <div className="bg-white rounded-lg border border-[#629FAD]/30 p-12 text-center shadow-sm">
            <Rss className="w-12 h-12 text-[#629FAD] mx-auto mb-4" />
            <h3 className="text-lg font-medium text-[#0C2C55] mb-2">No feeds added yet</h3>
            <p className="text-[#296374]">Add your first RSS feed to start discovering jobs automatically</p>
          </div>
        ) : (
          <div className="space-y-4">
            {feeds.map((feed) => (
              <div key={feed.id} className="bg-white border border-[#629FAD]/30 rounded-lg p-6 shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-[#E8E2DB] rounded-lg">
                      <Rss className="w-6 h-6 text-[#296374]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-[#0C2C55]">{feed.name}</h3>
                      <p className="text-sm text-[#296374] mt-1">{feed.url}</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handlePollFeed(feed.id)}
                      disabled={polling === feed.id}
                      className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 disabled:opacity-50 transition-colors"
                    >
                      <PlayCircle className="w-4 h-4" />
                      {polling === feed.id ? 'Polling...' : 'Poll'}
                    </button>
                    <button
                      onClick={() => handleDeleteFeed(feed.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
