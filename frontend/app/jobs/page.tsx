"use client"
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { RefreshCw, FileText, ExternalLink, Play, Trash2, Plus, Code, Copy, Check, RotateCcw, Eye } from 'lucide-react';
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { ResumePreviewPopup } from "@/components/ResumePreviewPopup";

interface Job {
    url: string;
    status: string;
    pdf_path: string | null;
    timestamp: string;
    details: string | null;
    error_message?: string | null;
    source_feed?: string | null;
    source_feed_name?: string | null;
    company_name?: string | null;
    job_title?: string | null;
    apply_link?: string | null;
}

interface Draft {
    id: string;
    job_url: string;
    apply_link?: string | null;
    status: string;
    field_count: number;
    filled_field_count: number;
    initial_ats_score?: number | null;
    current_ats_score?: number | null;
}

interface FullDraft {
    id: string;
    job_url: string;
    apply_link?: string | null;
    status: string;
    form_state: {
        version: string;
        job_url: string;
        page_index: number;
        fields: Array<{
            xpath: string;
            field_type: string;
            label: string | null;
            options: string[] | null;
            value: string | null;
            confidence: number;
            required: boolean;
            skipped: boolean;
            skip_reason: string | null;
        }>;
        extracted_at: string;
        last_modified: string;
    };
    resume_path: string | null;
    job_details: string | null;
    initial_ats_score: number | null;
    current_ats_score?: number | null;
    created_at: string;
    updated_at: string;
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
    const [viewDraftOpen, setViewDraftOpen] = useState(false);
    const [selectedDraft, setSelectedDraft] = useState<FullDraft | null>(null);
    const [loadingDraft, setLoadingDraft] = useState(false);
    const [copied, setCopied] = useState(false);
    const [previewOpen, setPreviewOpen] = useState(false);
    const [previewDraftId, setPreviewDraftId] = useState<string | null>(null);
    const [previewJobUrl, setPreviewJobUrl] = useState<string>("");

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

    const viewDraft = async (draftId: string) => {
        setLoadingDraft(true);
        setViewDraftOpen(true);
        try {
            const res = await axios.get(`${API_URL}/drafts/${draftId}`);
            setSelectedDraft(res.data);
        } catch (e) {
            console.error(e);
            toast.error("Failed to load draft details");
            setViewDraftOpen(false);
        } finally {
            setLoadingDraft(false);
        }
    };

    const copyToClipboard = () => {
        if (selectedDraft) {
            navigator.clipboard.writeText(JSON.stringify(selectedDraft, null, 2));
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
            toast.success("Copied to clipboard");
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
        if (status === 'Failed' || status === 'Error' || status === 'Draft Failed' || status === 'failed') return 'bg-red-50 text-red-700 border-red-200';
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
                    <table className="w-full text-sm text-left">
                        <thead className="bg-[#fdfdfd] text-muted-foreground uppercase text-[10px] tracking-widest font-bold border-b">
                            <tr>
                                <th className="px-4 py-3 font-bold">Date</th>
                                <th className="px-4 py-3 font-bold">Job</th>
                                <th className="px-4 py-3 font-bold text-center">Job Link</th>
                                <th className="px-4 py-3 font-bold text-center">Apply Link</th>
                                <th className="px-4 py-3 font-bold text-center">Fields</th>
                                <th className="px-4 py-3 font-bold text-center">Preview</th>
                                <th className="px-4 py-3 font-bold">Status</th>
                                <th className="px-4 py-3 font-bold text-center">Restart</th>
                                <th className="px-4 py-3 font-bold text-center">Open</th>
                                <th className="px-4 py-3 font-bold text-center">Delete</th>
                                <th className="px-4 py-3 font-bold text-center">JSON</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                            {loading && jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={11} className="px-6 py-12 text-center text-muted-foreground italic">
                                        Loading jobs...
                                    </td>
                                </tr>
                            ) : jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={11} className="px-6 py-12 text-center text-muted-foreground">
                                        No applications found yet. Add a job URL or configure RSS feeds to get started.
                                    </td>
                                </tr>
                            ) : (
                                jobs.map((job, i) => {
                                    const draft = getDraftForJob(job.url);
                                    const displayStatus = draft?.status || job.status;
                                    const isDraftReady = displayStatus === 'draft_saved' || displayStatus === 'user_opened';

                                    return (
                                        <tr key={i} className="group hover:bg-muted/30 transition-colors">
                                            {/* Date */}
                                            <td className="px-4 py-3 text-muted-foreground text-xs whitespace-nowrap">
                                                {new Date(job.timestamp).toLocaleDateString()}
                                            </td>

                                            {/* Job */}
                                            <td className="px-4 py-3">
                                                <div className="flex flex-col gap-0.5 min-w-0">
                                                    <span className="font-medium text-foreground truncate max-w-[280px]" title={job.job_title || job.url}>
                                                        {job.job_title || 'Untitled Position'}
                                                    </span>
                                                    <div className="flex items-center gap-2 text-xs text-muted-foreground truncate">
                                                        {job.company_name && (
                                                            <span className="font-medium">{job.company_name}</span>
                                                        )}
                                                        {(job.source_feed_name || job.source_feed) && (
                                                            <span className="text-muted-foreground/60" title={job.source_feed || ''}>
                                                                via {job.source_feed_name || (job.source_feed ? new URL(job.source_feed).hostname.replace('www.', '') : '')}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </td>

                                            {/* Job Link */}
                                            <td className="px-4 py-3 text-center">
                                                <a href={job.url} target="_blank" rel="noopener noreferrer"
                                                    className="inline-flex items-center justify-center text-muted-foreground hover:text-primary transition-colors"
                                                    title="View Job Description">
                                                    <FileText className="h-4 w-4" />
                                                </a>
                                            </td>

                                            {/* Application Link */}
                                            <td className="px-4 py-3 text-center">
                                                {job.apply_link ? (
                                                    <a href={job.apply_link} target="_blank" rel="noopener noreferrer"
                                                        className="inline-flex items-center justify-center text-blue-500 hover:text-blue-700 transition-colors"
                                                        title="Apply Page">
                                                        <ExternalLink className="h-4 w-4" />
                                                    </a>
                                                ) : (
                                                    <span className="text-muted-foreground/40">--</span>
                                                )}
                                            </td>

                                            {/* Fields Extracted / Total */}
                                            <td className="px-4 py-3 text-center whitespace-nowrap">
                                                {draft ? (
                                                    <span className="text-sm font-medium">
                                                        <span className="text-emerald-600">{draft.filled_field_count}</span>
                                                        <span className="text-muted-foreground"> / </span>
                                                        <span>{draft.field_count}</span>
                                                    </span>
                                                ) : (
                                                    <span className="text-muted-foreground/40">--</span>
                                                )}
                                            </td>

                                            {/* Preview Resume */}
                                            <td className="px-4 py-3 text-center">
                                                {draft ? (
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-7 w-7"
                                                        onClick={() => {
                                                            setPreviewDraftId(draft.id);
                                                            setPreviewJobUrl(job.url);
                                                            setPreviewOpen(true);
                                                        }}
                                                        title="Preview Resume"
                                                    >
                                                        <Eye className="h-4 w-4" />
                                                    </Button>
                                                ) : (
                                                    <span className="text-muted-foreground/40">--</span>
                                                )}
                                            </td>

                                            {/* Status */}
                                            <td className="px-4 py-3">
                                                <span className={cn(
                                                    "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border gap-1",
                                                    getStatusColor(displayStatus)
                                                )}>
                                                    {displayStatus.includes('Running') && (
                                                        <span className="relative flex h-1.5 w-1.5">
                                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                                                        </span>
                                                    )}
                                                    {displayStatus.replace('draft_', '').replace('_', ' ')}
                                                </span>
                                            </td>

                                            {/* Restart Workflow */}
                                            <td className="px-4 py-3 text-center">
                                                <Button
                                                    size="icon"
                                                    variant="ghost"
                                                    onClick={() => retryJob(job.url)}
                                                    className="h-7 w-7 text-muted-foreground hover:text-orange-600 hover:bg-orange-50"
                                                    title="Restart Workflow"
                                                >
                                                    <RotateCcw className="h-4 w-4" />
                                                </Button>
                                            </td>

                                            {/* Open Draft */}
                                            <td className="px-4 py-3 text-center">
                                                {isDraftReady && draft ? (
                                                    <Button
                                                        size="icon"
                                                        onClick={() => openDraft(draft.id, job.apply_link || job.url)}
                                                        disabled={openingDraft === draft.id}
                                                        className="h-7 w-7 bg-blue-600 hover:bg-blue-700 text-white"
                                                        title="Open Draft"
                                                    >
                                                        {openingDraft === draft.id ? (
                                                            <RefreshCw className="h-4 w-4 animate-spin" />
                                                        ) : (
                                                            <Play className="h-4 w-4" />
                                                        )}
                                                    </Button>
                                                ) : (
                                                    <span className="text-muted-foreground/40">--</span>
                                                )}
                                            </td>

                                            {/* Delete Job */}
                                            <td className="px-4 py-3 text-center">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-7 w-7 text-muted-foreground hover:text-red-600 hover:bg-red-50"
                                                    onClick={() => deleteJob(job.url)}
                                                    disabled={deletingJob === job.url}
                                                    title="Delete Job"
                                                >
                                                    {deletingJob === job.url ? (
                                                        <RefreshCw className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Trash2 className="h-4 w-4" />
                                                    )}
                                                </Button>
                                            </td>

                                            {/* Extracted JSON */}
                                            <td className="px-4 py-3 text-center">
                                                {draft ? (
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        onClick={() => viewDraft(draft.id)}
                                                        className="h-7 w-7"
                                                        title="View Extracted JSON"
                                                    >
                                                        <Code className="h-4 w-4" />
                                                    </Button>
                                                ) : (
                                                    <span className="text-muted-foreground/40">--</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </CardContent>
            </Card>

            {/* View Draft JSON Dialog */}
            <Dialog open={viewDraftOpen} onOpenChange={setViewDraftOpen}>
                <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Code className="h-5 w-5" />
                            Draft State JSON
                        </DialogTitle>
                    </DialogHeader>

                    {loadingDraft ? (
                        <div className="flex items-center justify-center py-12">
                            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : selectedDraft ? (
                        <div className="flex-1 overflow-hidden flex flex-col gap-4">
                            {/* Summary */}
                            <div className="grid grid-cols-3 gap-4 text-sm">
                                <div className="bg-muted/50 rounded-lg p-3">
                                    <div className="text-muted-foreground text-xs uppercase tracking-wide mb-1">Status</div>
                                    <div className="font-medium">{selectedDraft.status}</div>
                                </div>
                                <div className="bg-muted/50 rounded-lg p-3">
                                    <div className="text-muted-foreground text-xs uppercase tracking-wide mb-1">Total Fields</div>
                                    <div className="font-medium">{selectedDraft.form_state?.fields?.length || 0}</div>
                                </div>
                                <div className="bg-muted/50 rounded-lg p-3">
                                    <div className="text-muted-foreground text-xs uppercase tracking-wide mb-1">Filled Fields</div>
                                    <div className="font-medium">
                                        {selectedDraft.form_state?.fields?.filter(f => f.value && !f.skipped).length || 0}
                                    </div>
                                </div>
                            </div>

                            {/* Fields Table */}
                            {selectedDraft.form_state?.fields && selectedDraft.form_state.fields.length > 0 && (
                                <div className="border rounded-lg overflow-hidden">
                                    <div className="bg-muted/30 px-4 py-2 text-xs font-semibold uppercase tracking-wide border-b">
                                        Form Fields
                                    </div>
                                    <div className="max-h-[200px] overflow-y-auto">
                                        <table className="w-full text-sm">
                                            <thead className="bg-muted/20 text-xs sticky top-0">
                                                <tr>
                                                    <th className="px-3 py-2 text-left">Label</th>
                                                    <th className="px-3 py-2 text-left">Type</th>
                                                    <th className="px-3 py-2 text-left">Value</th>
                                                    <th className="px-3 py-2 text-left">XPath</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y">
                                                {selectedDraft.form_state.fields.map((field, i) => (
                                                    <tr key={i} className={cn(
                                                        "hover:bg-muted/20",
                                                        field.skipped && "bg-yellow-50/50"
                                                    )}>
                                                        <td className="px-3 py-2 font-medium">
                                                            {field.label || <span className="text-muted-foreground italic">No label</span>}
                                                            {field.required && <span className="text-red-500 ml-1">*</span>}
                                                        </td>
                                                        <td className="px-3 py-2 text-muted-foreground">{field.field_type}</td>
                                                        <td className="px-3 py-2">
                                                            {field.skipped ? (
                                                                <span className="text-yellow-600 text-xs">
                                                                    Skipped: {field.skip_reason}
                                                                </span>
                                                            ) : field.value ? (
                                                                <span className="text-green-700 truncate block max-w-[200px]" title={field.value}>
                                                                    {field.value}
                                                                </span>
                                                            ) : (
                                                                <span className="text-muted-foreground italic">Empty</span>
                                                            )}
                                                        </td>
                                                        <td className="px-3 py-2 text-xs text-muted-foreground font-mono truncate max-w-[150px]" title={field.xpath}>
                                                            {field.xpath}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* Raw JSON */}
                            <div className="flex-1 min-h-0 flex flex-col border rounded-lg overflow-hidden">
                                <div className="bg-muted/30 px-4 py-2 text-xs font-semibold uppercase tracking-wide border-b flex items-center justify-between">
                                    <span>Raw JSON</span>
                                    <Button size="sm" variant="ghost" onClick={copyToClipboard} className="h-7 px-2">
                                        {copied ? (
                                            <Check className="h-3 w-3 mr-1 text-green-600" />
                                        ) : (
                                            <Copy className="h-3 w-3 mr-1" />
                                        )}
                                        {copied ? "Copied!" : "Copy"}
                                    </Button>
                                </div>
                                <pre className="flex-1 overflow-auto p-4 text-xs bg-slate-950 text-slate-100 font-mono">
                                    {JSON.stringify(selectedDraft, null, 2)}
                                </pre>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            No draft data available
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            <ResumePreviewPopup
                isOpen={previewOpen}
                onClose={() => setPreviewOpen(false)}
                draftId={previewDraftId || ""}
                jobUrl={previewJobUrl}
            />
        </div>
    );
}
