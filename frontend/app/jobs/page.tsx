"use client";

import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/api";
import { Job } from "@/types/job";
import { toast } from "sonner";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useRouter } from "next/navigation";

export default function JobsPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);

    const { user, loading: authLoading, hasRole } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!authLoading) {
            // Check if user has any of the allowed roles
            if (!hasRole("customer") && !hasRole("basic") && !hasRole("admin")) {
                // Technically Sidebar hides this, but good to have protection
                toast.error("Unauthorized access");
                router.push("/dashboard");
                return;
            }
            loadJobs();
        }
    }, [authLoading, user]);

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
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="p-4">Loading jobs...</div>;

    return (
        <div>
            <h1 className="text-2xl font-bold mb-6">My Applications</h1>
            <div className="bg-card rounded-lg border text-card-foreground shadow-sm">
                <div className="relative w-full overflow-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Date</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Company</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Role</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Status</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Link</th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="p-4 text-center text-muted-foreground">No jobs found.</td>
                                </tr>
                            ) : (
                                jobs.map((job) => (
                                    <tr key={job.id} className="border-b transition-colors hover:bg-muted/50">
                                        <td className="p-4 align-middle">
                                            {new Date(job.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="p-4 align-middle font-medium">{job.company}</td>
                                        <td className="p-4 align-middle">{job.role}</td>
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
