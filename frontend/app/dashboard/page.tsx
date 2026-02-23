"use client";

import { useEffect, useState, useMemo } from "react";
import { fetchWithAuth } from "@/lib/api";
import { Job } from "@/types/job";
import { Feed } from "@/types/feed";
import { toast } from "sonner";
import Link from "next/link";
import { ExternalLink, Filter } from "lucide-react";
import { cn } from "@/lib/utils";

import { useFeeds } from "@/components/providers/feed-provider";

function formatDate(dateStr: string | undefined) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

export default function DashboardPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const { feeds, loading: feedsLoading } = useFeeds();
    const [selectedFeedId, setSelectedFeedId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadJobs().finally(() => setLoading(false));
    }, []);

    const loadJobs = async () => {
        try {
            const res = await fetchWithAuth("/jobs");
            if (res.ok) {
                const data = await res.json();
                setJobs(data);
            } else {
                toast.error("Failed to load jobs");
            }
        } catch (err) {
            toast.error("Error loading jobs");
        }
    };

    const filteredJobs = useMemo(() => {
        if (!selectedFeedId) return jobs;
        return jobs.filter(job => job.feed_id === selectedFeedId);
    }, [jobs, selectedFeedId]);

    if (loading || feedsLoading) return <div className="p-4">Loading dashboard...</div>;

    return (
        <div className="flex flex-col h-full space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">Dashboard</h1>

                {/* Dashboard-level Feed Filter */}
                <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-muted-foreground" />
                    <select
                        value={selectedFeedId || ""}
                        onChange={(e) => setSelectedFeedId(e.target.value || null)}
                        className="bg-background border border-input rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary min-w-[200px]"
                    >
                        <option value="">All Feeds</option>
                        {feeds.map((feed) => (
                            <option key={feed.id} value={feed.id}>
                                {feed.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Main Content */}
            <div className="bg-card rounded-lg border text-card-foreground shadow-sm">
                <div className="relative w-full overflow-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-40">Date</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Job Detail</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Status</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-24">Link</th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {filteredJobs.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="p-4 text-center text-muted-foreground">No jobs found.</td>
                                </tr>
                            ) : (
                                filteredJobs.map((job) => (
                                    <tr key={job.id} className="border-b transition-colors hover:bg-muted/50">
                                        <td className="p-4 align-middle whitespace-nowrap text-muted-foreground">
                                            {formatDate(job.timestamp || job.created_at)}
                                        </td>
                                        <td className="p-4 align-middle">
                                            <div className="font-bold text-slate-900">{job.role}</div>
                                            <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                                                Source: {feeds.find(f => f.id === job.feed_id)?.name || job.source_feed_name || 'Manual'}
                                            </div>
                                        </td>
                                        <td className="p-4 align-middle">
                                            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold
                                ${job.status === 'APPLIED' ? 'bg-green-100 text-green-800' :
                                                    job.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                                                        'bg-yellow-100 text-yellow-800'}`}>
                                                {job.status}
                                            </span>
                                        </td>
                                        <td className="p-4 align-middle">
                                            {job.url ? (
                                                <Link href={job.url} target="_blank" className="text-indigo-600 hover:text-indigo-900 flex items-center">
                                                    View <ExternalLink className="ml-1 h-3 w-3" />
                                                </Link>
                                            ) : '-'}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
