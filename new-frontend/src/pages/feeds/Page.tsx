import { useState, useEffect } from 'react';
import axios from 'axios';
import { Rss, Trash2, RefreshCw, PlayCircle, Loader2, FlaskConical } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { API_URL } from '@/lib/env';

// Test feed URL - always available
const TEST_FEED_URL = "http://localhost:8000/test/feed.xml";

interface Feed {
  // Frontend had url and name. Figma had id, name, url.
  // We'll use URL as ID if ID is missing, or generate one.
  // Backend returns { url, name }.
  url: string;
  name: string;
}

export default function RssFeedsPage() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [newFeedName, setNewFeedName] = useState("");
  const [newFeedUrl, setNewFeedUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [pollingAll, setPollingAll] = useState(false);
  const [pollingFeed, setPollingFeed] = useState<string | null>(null);



  // Filter out test feed from user feeds
  const userFeeds = feeds.filter(f => !f.url.includes('/test/feed.xml'));

  const fetchFeeds = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/feeds`);
      setFeeds(res.data);
    } catch (e) {
      console.error(e);
      toast.error("Failed to fetch feeds");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeeds();
  }, []);

  const addFeed = async () => {
    if (!newFeedUrl || !newFeedName) return;
    if (feeds.some(f => f.name === newFeedName)) {
      toast.error("A feed with this name already exists");
      return;
    }
    try {
      await axios.post(`${API_URL}/feeds`, { url: newFeedUrl, name: newFeedName });
      setNewFeedUrl("");
      setNewFeedName("");
      fetchFeeds();
      toast.success("Feed added successfully");
    } catch (e) {
      toast.error("Failed to add feed - URL or name may already exist");
    }
  };

  const removeFeed = async (feed: Feed) => {
    try {
      await axios.delete(`${API_URL}/feeds`, { data: { url: feed.url, name: feed.name } });
      fetchFeeds();
      toast.success("Feed removed");
    } catch (e) {
      toast.error("Failed to remove feed");
    }
  };

  const pollAllFeeds = async () => {
    setPollingAll(true);
    try {
      const res = await axios.post(`${API_URL}/feeds/poll`);
      toast.success(res.data.message);
    } catch (e) {
      toast.error("Failed to poll feeds");
    } finally {
      setPollingAll(false);
    }
  };

  const pollSingleFeed = async (url: string) => {
    setPollingFeed(url);
    try {
      const res = await axios.post(`${API_URL}/feeds/poll-single`, { url });
      if (res.data.jobs_found > 0) {
        toast.success(`Found ${res.data.jobs_found} new job(s)!`);
      } else {
        toast.info("No new jobs found in this feed");
      }
    } catch (e) {
      toast.error("Failed to poll feed");
    } finally {
      setPollingFeed(null);
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-semibold text-[#0C2C55] flex items-center gap-2">
             <Rss className="h-8 w-8 text-[#296374]" />
             RSS Feeds
          </h1>
          <div className="flex gap-3">
            <button
              onClick={pollAllFeeds}
              disabled={pollingAll || userFeeds.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {pollingAll ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                  <PlayCircle className="w-4 h-4" />
              )}
              {pollingAll ? 'Polling...' : 'Poll All'}
            </button>
            <button 
                onClick={fetchFeeds}
                className="flex items-center gap-2 px-4 py-2 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
            >
              <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
              Refresh
            </button>
          </div>
        </div>

        {/* Add Feed Form */}
        <div className="bg-white rounded-lg border border-[#629FAD]/30 p-6 mb-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#0C2C55] mb-4">Add New Feed</h2>
          <div className="flex flex-col md:flex-row gap-3">
            <input
              type="text"
              placeholder="Feed Name (e.g. Stripe)"
              value={newFeedName}
              onChange={(e) => setNewFeedName(e.target.value)}
              className="flex-1 px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374] bg-white text-[#0C2C55]"
            />
            <input
              type="url"
              placeholder="Feed URL (e.g. https://jobs.ashbyhq.com/...)"
              value={newFeedUrl}
              onChange={(e) => setNewFeedUrl(e.target.value)}
              className="flex-1 px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374] bg-white text-[#0C2C55]"
            />
            <button
              onClick={addFeed}
              disabled={!newFeedName || !newFeedUrl}
              className="px-6 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors disabled:opacity-50"
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
                <FlaskConical className="w-6 h-6 text-[#296374]" />
              </div>
              <div>
                <h3 className="font-semibold text-[#0C2C55]">Test Feed</h3>
                <p className="text-sm text-[#296374] mt-1">{TEST_FEED_URL}</p>
                <p className="text-sm text-[#296374] mt-2">Permanent test feed for verification</p>
              </div>
            </div>
            <button
              onClick={() => pollSingleFeed(TEST_FEED_URL)}
              disabled={pollingFeed === TEST_FEED_URL}
              className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 disabled:opacity-50 transition-colors"
            >
               {pollingFeed === TEST_FEED_URL ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                  <PlayCircle className="w-4 h-4" />
              )}
              {pollingFeed === TEST_FEED_URL ? 'Polling...' : 'Poll'}
            </button>
          </div>
        </div>

        {/* Feeds List */}
        {userFeeds.length === 0 && !loading ? (
          <div className="bg-white rounded-lg border border-[#629FAD]/30 p-12 text-center shadow-sm">
            <Rss className="w-12 h-12 text-[#629FAD] mx-auto mb-4" />
            <h3 className="text-lg font-medium text-[#0C2C55] mb-2">No feeds added yet</h3>
            <p className="text-[#296374]">Add your first RSS feed to start discovering jobs automatically</p>
          </div>
        ) : (
          <div className="space-y-4">
            {userFeeds.map((feed) => (
              <div key={feed.url} className="bg-white border border-[#629FAD]/30 rounded-lg p-6 shadow-sm">
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
                      onClick={() => pollSingleFeed(feed.url)}
                      disabled={pollingFeed === feed.url}
                      className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 disabled:opacity-50 transition-colors"
                    >
                      {pollingFeed === feed.url ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                          <PlayCircle className="w-4 h-4" />
                      )}
                      {pollingFeed === feed.url ? 'Polling...' : 'Poll'}
                    </button>
                    <button
                      onClick={() => removeFeed(feed)}
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
