"use client"
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, Download, FileText, AlertTriangle, ExternalLink, Play } from 'lucide-react';
import { cn } from "@/lib/utils";

interface Job {
    url: string;
    status: string;
    pdf_path: string | null;
    timestamp: string;
    details: string | null;
    error_message?: string | null;
}

interface Draft {
    id: string;
    job_url: string;
    status: string;
    field_count: number;
    filled_field_count: number;
}

export default function JobsPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [drafts, setDrafts] = useState<Draft[]>([]);
    const [loading, setLoading] = useState(true);
    const [openingDraft, setOpeningDraft] = useState<string | null>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchJobs = async () => {
        try {
            const [jobsRes, draftsRes] = await Promise.all([
                axios.get(`${API_URL}/jobs`),
                axios.get(`${API_URL}/drafts`)
            ]);
            setJobs(jobsRes.data);
            setDrafts(draftsRes.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    const retryJob = async (url: string) => {
        try {
            await axios.post(`${API_URL}/jobs/retry`, { url });
            fetchJobs();
        } catch (e) {
            alert("Failed to retry job");
        }
    };

    const openDraft = async (draftId: string, jobUrl: string) => {
        setOpeningDraft(draftId);

        // Use the browser extension trigger via URL hash
        // usage: URL#autoapply_id=UUID
        const separator = jobUrl.includes('#') ? '&' : '#';
        const triggerUrl = `${jobUrl}${separator}autoapply_id=${draftId}`;

        window.open(triggerUrl, '_blank');

        setOpeningDraft(null);

        // Show lightweight toast/helper
        // We assume the user has the extension. If not, page just opens.
        console.log("Opened with extension trigger");
    };

    // Find draft for a job URL
    const getDraftForJob = (jobUrl: string): Draft | undefined => {
        return drafts.find(d => d.job_url === jobUrl);
    };

    const getStatusColor = (status: string) => {
        if (status === 'Completed' || status === 'Applied') return 'bg-green-50 text-green-700 border-green-200';
        if (status === 'Draft Saved' || status === 'draft_saved') return 'bg-blue-50 text-blue-700 border-blue-200';
        if (status === 'Failed' || status === 'Error' || status === 'Draft Failed') return 'bg-red-50 text-red-700 border-red-200';
        if (status === 'Pending') return 'bg-yellow-50 text-yellow-700 border-yellow-200';
        return 'bg-gray-50 text-gray-700 border-gray-200';
    };

    return (
        <div className="space-y-8">
            <header className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground">Job History</h1>
                    <p className="text-muted-foreground">Track and manage your application drafts.</p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchJobs}
                    className="h-10 px-4"
                >
                    <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
                    Refresh
                </Button>
            </header>

            <Card className="shadow-sm border-border/60 overflow-hidden">
                <CardHeader className="border-b bg-muted/30 pb-4">
                    <CardTitle className="text-xl font-semibold">Application Drafts</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-[#fdfdfd] text-muted-foreground uppercase text-[10px] tracking-widest font-bold border-b">
                                <tr>
                                    <th className="px-6 py-4 font-bold">Date</th>
                                    <th className="px-6 py-4 font-bold">Status</th>
                                    <th className="px-6 py-4 font-bold">Fields</th>
                                    <th className="px-6 py-4 font-bold">Job URL</th>
                                    <th className="px-6 py-4 font-bold text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/40">
                                {loading && jobs.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground italic">
                                            Scanning for jobs...
                                        </td>
                                    </tr>
                                ) : jobs.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground">
                                            No applications found yet.
                                        </td>
                                    </tr>
                                ) : (
                                    jobs.map((job, i) => {
                                        const draft = getDraftForJob(job.url);
                                        return (
                                            <tr key={i} className="hover:bg-muted/30 transition-colors group">
                                                <td className="px-6 py-4 font-medium text-foreground/80">
                                                    {new Date(job.timestamp).toLocaleDateString(undefined, {
                                                        month: 'short',
                                                        day: 'numeric',
                                                        hour: '2-digit',
                                                        minute: '2-digit'
                                                    })}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={cn(
                                                        "inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider border",
                                                        getStatusColor(job.status)
                                                    )}>
                                                        {job.status}
                                                    </span>
                                                    {(job.status === 'Failed' || job.status === 'Draft Failed' || job.error_message) && (
                                                        <div className="mt-1.5 text-[11px] text-red-500/80 max-w-[200px] leading-tight" title={job.error_message || ""}>
                                                            <AlertTriangle className="h-3 w-3 inline mr-1 mb-0.5" />
                                                            {job.error_message}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    {draft ? (
                                                        <span className="text-sm">
                                                            <span className="font-semibold text-green-600">{draft.filled_field_count}</span>
                                                            <span className="text-muted-foreground">/{draft.field_count}</span>
                                                        </span>
                                                    ) : (
                                                        <span className="text-muted-foreground">-</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-2 max-w-[300px]">
                                                        <a
                                                            href={job.url}
                                                            target="_blank"
                                                            className="text-foreground/70 hover:text-accent font-medium truncate transition-colors decoration-accent/30 underline-offset-4 hover:underline"
                                                        >
                                                            {job.url}
                                                        </a>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <div className="flex items-center justify-end gap-1">
                                                        {/* Open Draft Button - show for Draft Saved status */}
                                                        {draft && (job.status === 'Draft Saved' || draft.status === 'draft_saved') && (
                                                            <Button
                                                                variant="default"
                                                                size="sm"
                                                                onClick={() => openDraft(draft.id, job.url)}
                                                                disabled={openingDraft === draft.id}
                                                                className="h-8 px-3 text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white"
                                                            >
                                                                {openingDraft === draft.id ? (
                                                                    <>
                                                                        <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                                                                        Opening...
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <Play className="h-3 w-3 mr-1" />
                                                                        Open Draft
                                                                    </>
                                                                )}
                                                            </Button>
                                                        )}

                                                        {job.pdf_path && (
                                                            <a
                                                                href={`${API_URL}/data/${job.pdf_path.split('/').pop()}`}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                            >
                                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-white" title="View PDF">
                                                                    <FileText className="h-4 w-4" />
                                                                </Button>
                                                            </a>
                                                        )}

                                                        {(job.status === 'Failed' || job.status === 'Draft Failed') && (
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => retryJob(job.url)}
                                                                className="h-8 px-3 text-xs font-bold text-accent hover:bg-accent/10"
                                                            >
                                                                Retry
                                                            </Button>
                                                        )}

                                                        {/* External link to job */}
                                                        <a href={job.url} target="_blank" rel="noopener noreferrer">
                                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" title="Open job page">
                                                                <ExternalLink className="h-4 w-4" />
                                                            </Button>
                                                        </a>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

