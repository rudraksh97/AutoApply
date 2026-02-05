import { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, Play, Pause, ExternalLink, Eye, FileText, RotateCw, Trash2, Code, Loader2, CheckCircle, Circle } from 'lucide-react';
import { toast } from 'sonner';

import { AddJobDialog } from '@/components/jobs/AddJobDialog';
import { DraftDetailsModal, FullDraft } from '@/components/jobs/DraftDetailsModal';
import { ResumePreviewPopup } from '@/components/jobs/ResumePreviewPopup';
import { API_URL } from '@/lib/env';

interface Job {
  url: string;
  status: string;
  timestamp: string;
  job_title?: string;
  company_name?: string;
  source_feed?: string;
  source_feed_name?: string;
  apply_link?: string;
  sent?: boolean;
  retry_count?: number;
  details?: string; // Job description
}

interface Draft {
   id: string;
   job_url: string;
   status: string;
   field_count: number;
   filled_field_count: number;
}

export default function JobsPage() {
  const [managerRunning, setManagerRunning] = useState(false);
  const [managerLoading, setManagerLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'drafts' | 'sent'>('drafts');
  
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [previewJob, setPreviewJob] = useState<Job | null>(null);
  
  // Draft Details State
  const [viewDraftOpen, setViewDraftOpen] = useState(false);
  const [selectedDraft, setSelectedDraft] = useState<FullDraft | null>(null);
  const [loadingDraft, setLoadingDraft] = useState(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = async () => {
    try {
      const [jobsRes, draftsRes, statusRes] = await Promise.all([
        axios.get(`${API_URL}/jobs`),
        axios.get(`${API_URL}/drafts`),
        axios.get(`${API_URL}/settings/job-manager/status`)
      ]);
      setJobs(jobsRes.data);
      setDrafts(draftsRes.data);
      setManagerRunning(statusRes.data.is_running);
    } catch (e) {
      console.error(e);
      // Don't toast on poll error to avoid spam
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleManager = async () => {
    setManagerLoading(true);
    try {
      if (managerRunning) {
        await axios.post(`${API_URL}/settings/job-manager/stop`);
        toast.success("Job Manager Paused");
      } else {
        await axios.post(`${API_URL}/settings/job-manager/start`);
        toast.success("Job Manager Started");
      }
      fetchJobs();
    } catch {
      toast.error("Failed to toggle manager");
    } finally {
      setManagerLoading(false);
    }
  };

  const markAsSent = async (url: string, sent: boolean) => {
    try {
        await axios.post(`${API_URL}/jobs/sent`, { url, sent });
        fetchJobs();
        toast.success(sent ? "Marked as sent" : "Unmarked as sent");
    } catch {
        toast.error("Failed to update job");
    }
  };

  const deleteJob = async (url: string) => {
    if (!confirm("Delete this job and its history?")) return;
    try {
      await axios.delete(`${API_URL}/jobs/`, { params: { url } });
      fetchJobs();
      toast.success("Job deleted");
    } catch {
      toast.error("Failed to delete job");
    }
  };

  const rerunJob = async (url: string) => {
    try {
      await axios.post(`${API_URL}/jobs/retry`, { url });
      fetchJobs();
      toast.success("Job queued for retry");
    } catch {
        toast.error("Failed to retry job");
    }
  };

  const addJob = async (url: string) => {
    try {
        const res = await axios.post(`${API_URL}/jobs/`, { url });
        setShowAddDialog(false);
        fetchJobs();
        if (res.data.status === 'exists') {
            toast.info("Job already exists (restarted)");
        } else {
            toast.success("Job added successfully");
        }
    } catch {
        toast.error("Failed to add job");
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

  const getDraftForJob = (jobUrl: string) => {
    return drafts.find(d => d.job_url === jobUrl);
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    let styles = 'bg-gray-100 text-gray-700';
    let label = status;

    if (s.includes('running') || s.includes('pending')) {
        styles = 'bg-blue-100 text-blue-700';
    } else if (s.includes('failed') || s.includes('error')) {
        styles = 'bg-red-100 text-red-700';
    } else if (s.includes('completed') || s.includes('applied') || s.includes('sent')) {
        styles = 'bg-green-100 text-green-700';
    } else if (s.includes('draft')) {
        styles = 'bg-yellow-100 text-yellow-800';
        label = 'Draft Ready';
    }

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium uppercase tracking-wide border border-transparent ${styles}`}>
        {label.replace(/_/g, ' ')}
      </span>
    );
  };

  const filteredJobs = jobs.filter(job => 
    activeTab === 'sent' ? job.sent : !job.sent
  );

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-semibold text-[#0C2C55]">Job History</h1>
          <button
            onClick={() => setShowAddDialog(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Job
          </button>
        </div>

        {/* Manager Status Banner */}
        <div className={`rounded-lg p-4 mb-6 transition-all ${managerRunning ? 'bg-green-50 border border-green-200' : 'bg-[#629FAD]/10 border border-[#629FAD]/30'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${managerRunning ? 'bg-green-100' : 'bg-[#629FAD]/20'}`}>
                {managerRunning ? (
                  <Play className="w-5 h-5 text-green-600" />
                ) : (
                  <Pause className="w-5 h-5 text-[#296374]" />
                )}
              </div>
              <div>
                <p className="font-semibold text-[#0C2C55]">
                  Job Manager: {managerRunning ? 'Running' : 'Paused'}
                </p>
                <p className="text-sm text-[#296374]">
                  {managerRunning 
                    ? 'Automatically processing application drafts' 
                    : 'Background processing is paused'
                  }
                </p>
              </div>
            </div>
            <button
              onClick={toggleManager}
              disabled={managerLoading}
              className={`px-6 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                managerRunning 
                  ? 'bg-[#629FAD]/20 text-[#0C2C55] hover:bg-[#629FAD]/30' 
                  : 'bg-[#0C2C55] text-[#E8E2DB] hover:bg-[#0C2C55]/90'
              }`}
            >
              {managerLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              {managerRunning ? 'Pause' : 'Start'}
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-[#629FAD]/30 mb-6">
          <div className="flex gap-8">
            <button
              onClick={() => setActiveTab('drafts')}
              className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
                activeTab === 'drafts'
                  ? 'border-[#0C2C55] text-[#0C2C55]'
                  : 'border-transparent text-[#629FAD] hover:text-[#296374]'
              }`}
            >
              Application Drafts ({jobs.filter(j => !j.sent).length})
            </button>
            <button
              onClick={() => setActiveTab('sent')}
              className={`pb-3 px-1 border-b-2 font-medium transition-colors ${
                activeTab === 'sent'
                  ? 'border-[#0C2C55] text-[#0C2C55]'
                  : 'border-transparent text-[#629FAD] hover:text-[#296374]'
              }`}
            >
              Sent Applications ({jobs.filter(j => j.sent).length})
            </button>
          </div>
        </div>

        {/* Jobs Table */}
        {loading && jobs.length === 0 ? (
            <div className="text-center py-12 text-[#296374]">Loading jobs...</div>
        ) : filteredJobs.length === 0 ? (
          <div className="bg-white rounded-lg border border-[#629FAD]/30 p-12 text-center shadow-sm">
            <FileText className="w-12 h-12 text-[#629FAD] mx-auto mb-4" />
            <h3 className="text-lg font-medium text-[#0C2C55] mb-2">
              No {activeTab === 'sent' ? 'sent applications' : 'drafts'} yet
            </h3>
            <p className="text-[#296374]">
              {activeTab === 'sent' 
                ? 'Mark applications as sent to track them here' 
                : 'Add job URLs or enable RSS feeds to start tracking applications'
              }
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-[#629FAD]/30 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-[#629FAD]/10 border-b border-[#629FAD]/30">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider text-center">Sent</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Job Details</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider text-center">Links</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider text-center">Fields</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#629FAD]/20">
                  {filteredJobs.map((job) => {
                    const draft = getDraftForJob(job.url);
                    const isDraft = activeTab === 'drafts';
                    
                    return (
                    <tr key={job.url} className="hover:bg-[#629FAD]/10 transition-colors">
                      <td className="px-6 py-4 text-center">
                        <button 
                            onClick={() => markAsSent(job.url, !isDraft)}
                            className="text-[#0C2C55] hover:text-[#296374] disabled:opacity-50"
                        >
                            {isDraft ? <Circle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5 text-green-600" />}
                        </button>
                      </td>
                      <td className="px-6 py-4 text-sm text-[#296374] whitespace-nowrap">
                        {new Date(job.timestamp).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-[#0C2C55]">{job.job_title || 'Untitled'}</div>
                        <div className="text-sm text-[#296374]">{job.company_name || 'Unknown Company'}</div>
                        {job.source_feed_name && (
                            <div className="text-xs text-[#629FAD] mt-1">via {job.source_feed_name}</div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex justify-center gap-2">
                          <a
                            href={job.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 text-[#296374] hover:bg-[#629FAD]/10 rounded transition-colors"
                            title="Job URL"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                          {job.apply_link && (
                            <a
                                href={job.apply_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-1.5 text-green-600 hover:bg-green-50 rounded transition-colors"
                                title="Apply Page"
                            >
                                <Play className="w-4 h-4" />
                            </a>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {getStatusBadge(draft?.status || job.status)}
                      </td>
                      <td className="px-6 py-4 text-center text-sm text-[#296374]">
                        {draft ? (
                            <span className={draft.filled_field_count === draft.field_count ? 'text-green-600 font-medium' : ''}>
                             {draft.filled_field_count} / {draft.field_count}
                            </span>
                        ) : (
                            <span className="text-muted-foreground/50">--</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex justify-center gap-1">
                          {draft && (
                              <button
                                onClick={() => viewDraft(draft.id)}
                                className="p-1.5 text-[#296374] hover:bg-[#629FAD]/10 rounded transition-colors"
                                title="View Data"
                              >
                                <Code className="w-4 h-4" />
                              </button>
                           )}
                           <button
                             onClick={() => setPreviewJob(job)}
                             className="p-1.5 text-[#296374] hover:bg-[#629FAD]/10 rounded transition-colors"
                             title="Preview"
                           >
                             <Eye className="w-4 h-4" />
                           </button>
                          <button
                            onClick={() => rerunJob(job.url)}
                            className="p-1.5 text-orange-600 hover:bg-orange-50 rounded transition-colors"
                            title="Rerun"
                          >
                            <RotateCw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deleteJob(job.url)}
                            className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <DraftDetailsModal 
        draft={selectedDraft} 
        isOpen={viewDraftOpen} 
        onClose={() => setViewDraftOpen(false)}
        loading={loadingDraft}
      />

      {showAddDialog && (
        <AddJobDialog 
          onClose={() => setShowAddDialog(false)}
          onAdd={addJob}
        />
      )}
      {previewJob && (
        <ResumePreviewPopup 
          isOpen={!!previewJob}
          onClose={() => setPreviewJob(null)}
          draftId={getDraftForJob(previewJob.url)?.id || ''}
          jobUrl={previewJob.url}
        />
      )}
    </div>
  );
}
