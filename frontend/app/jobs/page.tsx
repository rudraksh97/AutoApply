"use client"
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, Download, FileText, AlertTriangle } from 'lucide-react';
import { cn } from "@/lib/utils";

interface Job {
    url: string;
    status: string;
    pdf_path: string | null;
    timestamp: string;
    details: string | null;
    error_message?: string | null;
}

export default function JobsPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchJobs = async () => {
        try {
            const res = await axios.get(`${API_URL}/jobs`);
            setJobs(res.data);
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

    const getStatusColor = (status: string) => {
        if (status === 'Completed' || status === 'Applied') return 'text-green-600 bg-green-100';
        if (status === 'Failed' || status === 'Error') return 'text-red-600 bg-red-100';
        if (status === 'Pending') return 'text-yellow-600 bg-yellow-100';
        return 'text-blue-600 bg-blue-100';
    };

    return (
        <div className="space-y-8">
            <header className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground">Job History</h1>
                    <p className="text-muted-foreground">Track and manage your recent job applications.</p>
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
                    <CardTitle className="text-xl font-semibold">Active Applications</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-[#fdfdfd] text-muted-foreground uppercase text-[10px] tracking-widest font-bold border-b">
                                <tr>
                                    <th className="px-6 py-4 font-bold">Date</th>
                                    <th className="px-6 py-4 font-bold">Status</th>
                                    <th className="px-6 py-4 font-bold">Job URL</th>
                                    <th className="px-6 py-4 font-bold text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/40">
                                {loading && jobs.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center text-muted-foreground italic">
                                            Scanning for jobs...
                                        </td>
                                    </tr>
                                ) : jobs.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center text-muted-foreground">
                                            No applications found yet.
                                        </td>
                                    </tr>
                                ) : (
                                    jobs.map((job, i) => (
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
                                                    job.status === 'Applied' || job.status === 'Completed'
                                                        ? 'bg-green-50 text-green-700 border-green-200'
                                                        : job.status === 'Failed' || job.status === 'Error'
                                                            ? 'bg-red-50 text-red-700 border-red-200'
                                                            : 'bg-yellow-50 text-yellow-700 border-yellow-200'
                                                )}>
                                                    {job.status}
                                                </span>
                                                {(job.status === 'Failed' || job.error_message) && (
                                                    <div className="mt-1.5 text-[11px] text-red-500/80 max-w-[200px] leading-tight" title={job.error_message || ""}>
                                                        <AlertTriangle className="h-3 w-3 inline mr-1 mb-0.5" />
                                                        {job.error_message}
                                                    </div>
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
                                                <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
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

                                                    {(job.status === 'Failed') && (
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => retryJob(job.url)}
                                                            className="h-8 px-3 text-xs font-bold text-accent hover:bg-accent/10"
                                                        >
                                                            Retry
                                                        </Button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
