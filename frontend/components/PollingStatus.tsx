'use client';

import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface PollStatus {
    last_poll_time: number;
    total_polls: number;
    last_jobs_found: number;
    is_polling: boolean;
}

export default function PollingStatus() {
    const [status, setStatus] = useState<PollStatus | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchStatus = async () => {
        try {
            const response = await axios.get('/api/feeds/status');
            setStatus(response.data);
        } catch (error) {
            console.error('Failed to fetch polling status', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    if (loading && !status) return <div className="text-xs text-gray-500">Checking poller status...</div>;
    if (!status) return null;

    const timeAgo = (timestamp: number) => {
        if (!timestamp) return 'Never';
        const seconds = Math.floor((Date.now() / 1000) - timestamp);
        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        return `${Math.floor(seconds / 3600)}h ago`;
    };

    return (
        <div className="bg-base-200 rounded-lg p-3 flex items-center justify-between text-sm shadow-sm border border-base-300 mb-4">
            <div className="flex items-center gap-2">
                {status.is_polling ? (
                    <span className="loading loading-spinner loading-xs text-primary"></span>
                ) : (
                    <div className="w-2 h-2 rounded-full bg-green-500 indicator-item"></div>
                )}
                <span className="font-medium">Background Poller</span>
            </div>

            <div className="flex gap-4 text-xs opacity-80">
                <div>
                    Last Run: <span className="font-mono font-bold">{timeAgo(status.last_poll_time)}</span>
                </div>
                <div>
                    Jobs Found: <span className="font-mono font-bold">{status.last_jobs_found}</span>
                </div>
                <div>
                    Total Polls: <span className="font-mono">{status.total_polls}</span>
                </div>
            </div>
        </div>
    );
}
