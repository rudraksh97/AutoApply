"use client"
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { RefreshCw, Download, FileText, AlertTriangle, ExternalLink, Play, Trash2, Plus } from 'lucide-react';
import { toast } from "sonner";
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
    const [newJobUrl, setNewJobUrl] = useState("");
    const [addingJob, setAddingJob] = useState(false);
    const [addJobOpen, setAddJobOpen] = useState(false);
    const [deletingJob, setDeletingJob] = useState<string | null>(null);

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
            toast.error("Failed to retry job");
        }
    };

    const addJob = async () => {
        if (!newJobUrl) return;
        setAddingJob(true);
        try {
            // 1. Add job to DB
            const res = await axios.post(`${API_URL}/jobs/`, { url: newJobUrl });

            setNewJobUrl("");
            setAddJobOpen(false);
            fetchJobs();

            if (res.data.status === 'exists') {
                toast.info("Job already exists (workflow restarted)");
            }
        } catch (e) {
            console.error(e);
            toast.error("Failed to add job");
        } finally {
            setAddingJob(false);
        }
    };

    const deleteJob = async (url: string) => {
        if (!confirm("Are you sure you want to delete this job and its history?")) return;
        setDeletingJob(url);
        try {
            await axios.delete(`${API_URL}/jobs/`, { params: { url } });
            fetchJobs();
        } catch (e) {
            console.error(e);
            toast.error("Failed to delete job");
        } finally {
            setDeletingJob(null);
        }
    };

    const openDraft = async (draftId: string, jobUrl: string) => {
        setOpeningDraft(draftId);

        // Use the browser extension trigger via URL hash
        // usage: URL#autoapply_id=UUID

        // Special handling for Ashby: user should open on /application URL
        let targetUrl = jobUrl;
        if (targetUrl.includes("jobs.ashbyhq.com") && !targetUrl.includes("/application")) {
            // Remove trailing slash if present then append /application
            targetUrl = targetUrl.replace(/\/$/, "") + "/application";
        }

        const separator = targetUrl.includes('#') ? '&' : '#';
        const triggerUrl = `${targetUrl}${separator}autoapply_id=${draftId}`;

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
        if (status.includes('Running')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
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
                <div className="flex items-center gap-2">
                    <Dialog open={addJobOpen} onOpenChange={setAddJobOpen}>
                        <DialogTrigger asChild>
                            <Button className="h-10 px-4">
                                <Plus className="h-4 w-4 mr-2" />
                                Add Job
                            </Button>
                        </DialogTrigger>
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>Add New Job</DialogTitle>
                            </DialogHeader>
                            <div className="py-4">
                                <Input
                                    placeholder="https://jobs.ashbyhq.com/..."
                                    value={newJobUrl}
                                    onChange={(e) => setNewJobUrl(e.target.value)}
                                />
                                <p className="text-sm text-muted-foreground mt-2">
                                    Adding a job will automatically trigger the draft preparation workflow.
                                </p>
                            </div>
                            <DialogFooter>
                                <Button variant="outline" onClick={() => setAddJobOpen(false)}>Cancel</Button>
                                <Button onClick={addJob} disabled={addingJob || !newJobUrl}>
                                    {addingJob ? "Adding..." : "Add Job"}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>

                    <Button
                        variant="outline"
                        size="sm"
                        onClick={fetchJobs}
                        className="h-10 px-4"
                    >
                        <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
                        Refresh
                    </Button>
                </div>
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
                                        const displayStatus = draft?.status || job.status;
                                        const isDraftReady = displayStatus === 'draft_saved' || displayStatus === 'user_opened';

                                        return (
                                            <tr key={i} className="group hover:bg-muted/30 transition-colors">
                                                <td className="px-6 py-4 text-muted-foreground whitespace-nowrap">
                                                    {new Date(job.timestamp).toLocaleDateString()}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={cn(
                                                        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border shadow-sm gap-1.5",
                                                        getStatusColor(displayStatus)
                                                    )}>
                                                        {displayStatus.includes('Running') && (
                                                            <span className="relative flex h-2 w-2">
                                                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                                                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                                            </span>
                                                        )}
                                                        {displayStatus}
                                                    </span>
                                                    {draft?.status && draft.status !== job.status && (
                                                        <div className="text-[10px] text-muted-foreground mt-1">
                                                            Draft: {draft.status}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    {draft ? (
                                                        <span className="text-muted-foreground">
                                                            {draft.filled_field_count} filled
                                                        </span>
                                                    ) : (
                                                        <span className="text-muted-foreground">-</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 max-w-[300px]">
                                                    <div className="flex items-center gap-2">
                                                        <a href={job.url} target="_blank" rel="noopener noreferrer"
                                                            className="text-primary hover:underline font-medium truncate block"
                                                            title={job.url}>
                                                            {job.url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}...
                                                        </a>
                                                        <ExternalLink className="h-3 w-3 text-muted-foreground/60 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <div className="flex items-center justify-end gap-2">
                                                        {isDraftReady && draft && (
                                                            <Button
                                                                size="sm"
                                                                onClick={() => openDraft(draft.id, job.url)}
                                                                disabled={openingDraft === draft.id}
                                                                className="h-8 bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
                                                            >
                                                                {openingDraft === draft.id ? (
                                                                    <RefreshCw className="h-3 w-3 animate-spin mr-1" />
                                                                ) : (
                                                                    <Play className="h-3 w-3 mr-1" />
                                                                )}
                                                                Open Draft
                                                            </Button>
                                                        )}

                                                        {job.pdf_path && (
                                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                                                                <Download className="h-4 w-4" />
                                                            </Button>
                                                        )}

                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-8 w-8 text-muted-foreground hover:text-red-600 hover:bg-red-50"
                                                            onClick={() => deleteJob(job.url)}
                                                            disabled={deletingJob === job.url}
                                                        >
                                                            {deletingJob === job.url ? (
                                                                <RefreshCw className="h-4 w-4 animate-spin" />
                                                            ) : (
                                                                <Trash2 className="h-4 w-4" />
                                                            )}
                                                        </Button>
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
