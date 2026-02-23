"use client";

import { useEffect, useState, useMemo } from "react";
import { fetchWithAuth } from "@/lib/api";
import { Job } from "@/types/job";
import { toast } from "sonner";
import Link from "next/link";
import { ExternalLink, Play, Pause, Loader2, RotateCw, CheckCircle, Circle, Trash2, Search, Filter } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useRouter } from "next/navigation";
import { useFeeds } from "@/components/providers/feed-provider";

function formatDate(dateStr: string | undefined) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

export default function JobsPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [managerStatus, setManagerStatus] = useState<any>(null);
    const [managerLoading, setManagerLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<'drafts' | 'sent'>('drafts');
    const [searchQuery, setSearchQuery] = useState("");
    const { feeds } = useFeeds();
    const [selectedFeedId, setSelectedFeedId] = useState<string | null>(null);

    const { user, loading: authLoading } = useAuth();
    const router = useRouter();

    const managerRunning = managerStatus?.is_running || false;
    const isAdmin = user?.roles?.includes('admin') ?? false;

    // Admins see all feeds; others see only their personal feeds
    const availableFeeds = useMemo(() => {
        if (!user) return [];
        if (isAdmin) return feeds;
        return feeds.filter(f => !f.is_global && f.user_id === user.id);
    }, [feeds, user, isAdmin]);

    useEffect(() => {
        if (!authLoading && user) {
            loadJobs();
            fetchManagerStatus();
            const interval = setInterval(() => {
                loadJobs();
                fetchManagerStatus();
            }, 5000);
            return () => clearInterval(interval);
        }
    }, [authLoading, user]);

    const loadJobs = async () => {
        try {
            const res = await fetchWithAuth("/jobs");
            if (res.ok) {
                const data = await res.json();
                setJobs(data || []);
            }
        } catch (err) {
            console.error("Error loading jobs", err);
        } finally {
            setLoading(false);
        }
    };

    const fetchManagerStatus = async () => {
        try {
            const res = await fetchWithAuth("/settings/job-manager/status");
            if (res.ok) {
                const data = await res.json();
                setManagerStatus(data);
            }
        } catch (err) {
            console.error("Error fetching manager status", err);
        }
    };

    const toggleManager = async () => {
        setManagerLoading(true);
        try {
            const endpoint = managerRunning ? "/settings/job-manager/stop" : "/settings/job-manager/start";
            const res = await fetchWithAuth(endpoint, { method: "POST" });
            if (res.ok) {
                toast.success(managerRunning ? "Job Manager Paused" : "Job Manager Started");
                fetchManagerStatus();
            } else {
                const data = await res.json();
                toast.error(data.detail || "Failed to toggle manager");
            }
        } catch {
            toast.error("Failed to toggle manager");
        } finally {
            setManagerLoading(false);
        }
    };

    const rerunJob = async (url: string) => {
        try {
            const res = await fetchWithAuth("/jobs/retry", {
                method: "POST",
                body: JSON.stringify({ url })
            });
            if (res.ok) {
                toast.success("Job queued for processing");
                loadJobs();
            } else {
                const data = await res.json();
                toast.error(data.detail || "Failed to start processing");
            }
        } catch {
            toast.error("Failed to retry job");
        }
    };

    const markAsSent = async (url: string, sent: boolean) => {
        try {
            const res = await fetchWithAuth("/jobs/sent", {
                method: "POST",
                body: JSON.stringify({ url, sent })
            });
            if (res.ok) {
                toast.success(sent ? "Marked as sent" : "Unmarked as sent");
                loadJobs();
            }
        } catch {
            toast.error("Failed to update job");
        }
    };

    const deleteJob = async (url: string) => {
        if (!confirm("Delete this job and its history?")) return;
        try {
            const res = await fetchWithAuth(`/jobs?url=${encodeURIComponent(url)}`, {
                method: "DELETE"
            });
            if (res.ok) {
                toast.success("Job deleted");
                loadJobs();
            }
        } catch {
            toast.error("Failed to delete job");
        }
    };

    const filteredJobs = useMemo(() => {
        return jobs.filter(job => {
            const matchesTab = activeTab === 'sent' ? job.sent : !job.sent;
            const matchesFeed = !selectedFeedId || job.feed_id === selectedFeedId;
            const matchesSearch = (job.role || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                (job.url && job.url.toLowerCase().includes(searchQuery.toLowerCase()));
            return matchesTab && matchesFeed && matchesSearch;
        });
    }, [jobs, activeTab, selectedFeedId, searchQuery]);

    if (loading && jobs.length === 0) return <div className="p-4">Loading jobs...</div>;

    return (
        <div className="flex flex-col h-full space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-900">Process Jobs</h1>

                {/* Local Feed Filter for Personal Feeds */}
                <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4 text-slate-400" />
                    <select
                        value={selectedFeedId || ""}
                        onChange={(e) => setSelectedFeedId(e.target.value || null)}
                        className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[200px] shadow-sm cursor-pointer transition-all"
                    >
                        <option value="">{isAdmin ? "All System Feeds" : "All Personal Feeds"}</option>
                        {availableFeeds.map((feed) => (
                            <option key={feed.id} value={feed.id}>
                                {feed.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Manager Status Banner */}
            <div className={`rounded-xl p-5 transition-all border shadow-sm flex items-center justify-between ${managerRunning ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'}`}>
                <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-lg flex items-center justify-center ${managerRunning ? 'bg-emerald-100' : 'bg-slate-200'}`}>
                        {managerRunning ? (
                            <Play className="w-5 h-5 text-emerald-600 fill-emerald-600" />
                        ) : (
                            <Pause className="w-5 h-5 text-slate-600 fill-slate-600" />
                        )}
                    </div>
                    <div>
                        <p className="font-bold text-slate-900">
                            Job Manager: {managerRunning ? 'Running' : 'Paused'}
                        </p>
                        <p className="text-sm text-slate-600">
                            {managerRunning
                                ? 'Automatically processing application drafts in the background'
                                : 'Processing is paused. Pending jobs will not be processed.'
                            }
                        </p>
                    </div>
                </div>
                <button
                    onClick={toggleManager}
                    disabled={managerLoading}
                    className={`px-6 py-2 rounded-lg font-semibold transition-all flex items-center gap-2 shadow-sm ${managerRunning
                        ? 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
                        : 'bg-indigo-600 text-white hover:bg-indigo-700'
                        }`}
                >
                    {managerLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                    {managerRunning ? 'Pause Manager' : 'Start Processing'}
                </button>
            </div>

            {/* Filters and Tabs Row */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                {/* Tabs */}
                <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200">
                    <button
                        onClick={() => setActiveTab('drafts')}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'drafts'
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        Drafts ({jobs.filter(j => !j.sent).length})
                    </button>
                    <button
                        onClick={() => setActiveTab('sent')}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'sent'
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        Sent ({jobs.filter(j => j.sent).length})
                    </button>
                </div>

                {/* Search Input */}
                <div className="relative w-full sm:w-64">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Search jobs..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                </div>
            </div>

            {/* Jobs Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex-1">
                <div className="relative w-full overflow-auto h-full">
                    <table className="w-full text-sm">
                        <thead className="bg-slate-50 border-b border-slate-200 sticky top-0 z-10">
                            <tr>
                                <th className="h-12 px-4 text-center align-middle font-semibold text-slate-700 w-16">Sent</th>
                                <th className="h-12 px-4 text-left align-middle font-semibold text-slate-700">Date</th>
                                <th className="h-12 px-4 text-left align-middle font-semibold text-slate-700">Job Detail</th>
                                <th className="h-12 px-4 text-left align-middle font-semibold text-slate-700">Status</th>
                                <th className="h-12 px-4 text-center align-middle font-semibold text-slate-700 w-24">Link</th>
                                <th className="h-12 px-4 text-center align-middle font-semibold text-slate-700 w-24">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-600">
                            {filteredJobs.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="p-12 text-center text-slate-400">
                                        <div className="flex flex-col items-center gap-2">
                                            <div className="p-4 bg-slate-50 rounded-full">
                                                <RotateCw className="w-8 h-8 text-slate-300" />
                                            </div>
                                            <p className="font-medium text-slate-900">No applications found</p>
                                            <p className="text-sm">Try adjusting your filters or adding a new job URL.</p>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                filteredJobs.map((job) => (
                                    <tr key={job.id || job.url} className="transition-colors hover:bg-slate-50/50">
                                        <td className="p-4 align-middle text-center">
                                            <button
                                                onClick={() => markAsSent(job.url, !job.sent)}
                                                className="transition-colors"
                                            >
                                                {job.sent ? (
                                                    <CheckCircle className="w-6 h-6 text-emerald-500" />
                                                ) : (
                                                    <Circle className="w-6 h-6 text-slate-300 hover:text-slate-400" />
                                                )}
                                            </button>
                                        </td>
                                        <td className="p-4 align-middle whitespace-nowrap text-slate-400 text-xs text-left">
                                            {formatDate(job.created_at || job.timestamp)}
                                        </td>
                                        <td className="p-4 align-middle text-left">
                                            <div className="font-bold text-slate-900">{job.role || 'Unknown Role'}</div>
                                            <div className="text-xs text-slate-400 mt-0.5">
                                                Source: {feeds.find(f => f.id === job.feed_id)?.name || job.source_feed_name || 'Manual Ingestion'}
                                            </div>
                                        </td>
                                        <td className="p-4 align-middle text-left">
                                            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider
                                                    ${job.status === 'APPLIED' || job.status?.toLowerCase().includes('completed') ? 'bg-emerald-100 text-emerald-700' :
                                                    job.status === 'FAILED' || job.status?.toLowerCase().includes('error') ? 'bg-rose-100 text-rose-700' :
                                                        'bg-amber-100 text-amber-700'}`}>
                                                {job.status?.replace(/_/g, ' ')}
                                            </span>
                                        </td>
                                        <td className="p-4 align-middle text-center">
                                            {job.url ? (
                                                <Link href={job.url} target="_blank" className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg inline-flex transition-colors">
                                                    <ExternalLink className="h-5 w-5" />
                                                </Link>
                                            ) : '-'}
                                        </td>
                                        <td className="p-4 align-middle text-center">
                                            <div className="flex items-center justify-center gap-1">
                                                <button
                                                    onClick={() => rerunJob(job.url)}
                                                    className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                                    title="Retry Job"
                                                >
                                                    <Play className="h-5 w-5" />
                                                </button>
                                                <button
                                                    onClick={() => deleteJob(job.url)}
                                                    className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                                                    title="Delete"
                                                >
                                                    <Trash2 className="h-5 w-5" />
                                                </button>
                                            </div>
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
