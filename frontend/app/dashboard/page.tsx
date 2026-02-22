"use client";

import { useEffect, useState, useMemo } from "react";
import { fetchWithAuth } from "@/lib/api";
import { Job } from "@/types/job";
import { Feed } from "@/types/feed";
import { toast } from "sonner";
import Link from "next/link";
import { ExternalLink, Filter } from "lucide-react";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [feeds, setFeeds] = useState<Feed[]>([]);
    const [selectedFeedId, setSelectedFeedId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([loadJobs(), loadFeeds()]).finally(() => setLoading(false));
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

    const loadFeeds = async () => {
        try {
            const res = await fetchWithAuth("/feeds");
            if (res.ok) {
                const data = await res.json();
                setFeeds(data);
            }
        } catch (err) {
            console.error("Error loading feeds", err);
        }
    };

    const filteredJobs = useMemo(() => {
        if (!selectedFeedId) return jobs;
        return jobs.filter(job => job.feed_id === selectedFeedId); // Assuming feed_id is present in Job
    }, [jobs, selectedFeedId]);

    if (loading) return <div className="p-4">Loading dashboard...</div>;

    return (
        <div className="flex h-full gap-6">
            {/* Filters Sidebar */}
            <aside className="w-64 flex-none hidden lg:block">
                <div className="font-semibold mb-4 flex items-center gap-2">
                    <Filter className="h-4 w-4" /> Filters
                </div>
                <div className="space-y-1">
                    <button
                        onClick={() => setSelectedFeedId(null)}
                        className={cn(
                            "w-full text-left px-3 py-2 rounded-md text-sm transition-colors",
                            !selectedFeedId ? "bg-secondary text-secondary-foreground font-medium" : "hover:bg-muted text-muted-foreground"
                        )}
                    >
                        All Feeds
                    </button>
                    {feeds.map(feed => (
                        <button
                            key={feed.id || feed.url}
                            onClick={() => setSelectedFeedId(feed.id || null)} // Backend might return ID
                            className={cn(
                                "w-full text-left px-3 py-2 rounded-md text-sm transition-colors truncate",
                                selectedFeedId === feed.id ? "bg-secondary text-secondary-foreground font-medium" : "hover:bg-muted text-muted-foreground"
                            )}
                        >
                            {feed.name || feed.url}
                        </button>
                    ))}
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 min-w-0">
                <h1 className="text-2xl font-bold mb-6">Job History</h1>

                <div className="bg-card rounded-lg border text-card-foreground shadow-sm">
                    <div className="relative w-full overflow-auto">
                        <table className="w-full caption-bottom text-sm">
                            <thead className="[&_tr]:border-b">
                                <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Date</th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Company</th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Role</th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground hidden sm:table-cell">Source</th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Status</th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Link</th>
                                </tr>
                            </thead>
                            <tbody className="[&_tr:last-child]:border-0">
                                {filteredJobs.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="p-4 text-center text-muted-foreground">No jobs found.</td>
                                    </tr>
                                ) : (
                                    filteredJobs.map((job) => (
                                        <tr key={job.id} className="border-b transition-colors hover:bg-muted/50">
                                            <td className="p-4 align-middle whitespace-nowrap">
                                                {new Date(job.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="p-4 align-middle font-medium">{job.company}</td>
                                            <td className="p-4 align-middle">{job.role}</td>
                                            <td className="p-4 align-middle hidden sm:table-cell max-w-[150px] truncate text-muted-foreground">
                                                {feeds.find(f => f.id === job.feed_id)?.name || job.feed_id || '-'}
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
        </div>
    );
}
