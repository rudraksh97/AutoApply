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
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Job History</h1>
                <Button variant="outline" size="sm" onClick={fetchJobs}><RefreshCw className="h-4 w-4 mr-2" /> Refresh</Button>
            </div>

            <Card className="w-full">
                <CardHeader>
                    <CardTitle>Applications</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border overflow-x-auto">
                        <table className="w-full text-sm text-left table-fixed">
                            <thead className="bg-muted/50 text-muted-foreground">
                                <tr>
                                    <th className="p-4 font-medium">Date</th>
                                    <th className="p-4 font-medium">Status</th>
                                    <th className="p-4 font-medium">Job URL</th>
                                    <th className="p-4 font-medium">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && jobs.length === 0 ? (
                                    <tr><td colSpan={4} className="p-4 text-center">Loading...</td></tr>
                                ) : jobs.length === 0 ? (
                                    <tr><td colSpan={4} className="p-4 text-center">No jobs found.</td></tr>
                                ) : (
                                    jobs.map((job, i) => (
                                        <tr key={i} className="border-t hover:bg-muted/50">
                                            <td className="p-4 whitespace-nowrap">{job.timestamp}</td>
                                            <td className="p-4">
                                                <span className={cn("px-2 py-1 rounded-full text-xs font-semibold", getStatusColor(job.status))}>
                                                    {job.status}
                                                </span>
                                                {(job.status === 'Failed' || job.error_message) && (
                                                    <div className="mt-1 text-xs text-red-500 max-w-xs truncate" title={job.error_message || ""}>
                                                        {job.error_message}
                                                    </div>
                                                )}
                                            </td>
                                            <td className="p-4 max-w-xs truncate" title={job.url}>
                                                <a href={job.url} target="_blank" className="text-blue-600 hover:underline flex items-center">
                                                    {job.url}
                                                </a>
                                            </td>
                                            <td className="p-4 flex items-center gap-2">
                                                {job.pdf_path && (
                                                    <a
                                                        href={`${API_URL}/data/${job.pdf_path.split('/').pop()}`}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                    >
                                                        <Button variant="ghost" size="icon" title="Download Resume">
                                                            <FileText className="h-4 w-4" />
                                                        </Button>
                                                    </a>
                                                )}

                                                {(job.status === 'Failed') && (
                                                    <Button variant="outline" size="sm" onClick={() => retryJob(job.url)}>
                                                        Retry
                                                    </Button>
                                                )}
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
