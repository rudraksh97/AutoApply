"use client";
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import { Plus, Play, Pause, ExternalLink, Eye, FileText, RotateCw, Trash2, Code } from 'lucide-react';
import { JobJsonModal } from './JobJsonModal';
import { AddJobDialog } from './AddJobDialog';
import { ResumePreviewPopup } from './ResumePreviewPopup';

interface Job {
  id: string;
  sent: boolean;
  date: string;
  title: string;
  company: string;
  source: string;
  jobUrl: string;
  applyUrl: string;
  status: 'draft' | 'running' | 'failed' | 'completed';
  retryCount: number;
  filledFields: number;
  totalFields: number;
  formData?: any;
}

export function JobHistoryPage() {
  const [managerRunning, setManagerRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'drafts' | 'sent'>('drafts');
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [previewJob, setPreviewJob] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([
    {
      id: '1',
      sent: false,
      date: '2026-01-27 10:30',
      title: 'Senior Frontend Developer',
      company: 'TechCorp Inc.',
      source: 'LinkedIn Jobs',
      jobUrl: 'https://example.com/job/123',
      applyUrl: 'https://example.com/apply/123',
      status: 'completed',
      retryCount: 0,
      filledFields: 12,
      totalFields: 15,
      formData: {
        personalInfo: { name: 'John Doe', email: 'john@example.com' },
        confidence: 0.95
      }
    },
    {
      id: '2',
      sent: false,
      date: '2026-01-27 09:15',
      title: 'React Developer',
      company: 'StartupXYZ',
      source: 'Test Feed',
      jobUrl: 'https://example.com/job/456',
      applyUrl: 'https://example.com/apply/456',
      status: 'failed',
      retryCount: 2,
      filledFields: 8,
      totalFields: 15,
    }
  ]);

  const getStatusBadge = (status: string) => {
    const styles = {
      draft: 'bg-gray-100 text-gray-700',
      running: 'bg-blue-100 text-blue-700',
      failed: 'bg-red-100 text-red-700',
      completed: 'bg-green-100 text-green-700',
    };
    const labels = {
      draft: 'Draft Saved',
      running: 'Running',
      failed: 'Failed',
      completed: 'Completed',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status as keyof typeof styles]}`}>
        {labels[status as keyof typeof labels]}
      </span>
    );
  };

  const toggleSent = (id: string) => {
    setJobs(jobs.map(job => 
      job.id === id ? { ...job, sent: !job.sent } : job
    ));
  };

  const deleteJob = (id: string) => {
    setJobs(jobs.filter(job => job.id !== id));
  };

  const rerunJob = (id: string) => {
    setJobs(jobs.map(job => 
      job.id === id ? { ...job, status: 'running', retryCount: job.retryCount + 1 } : job
    ));
    setTimeout(() => {
      setJobs(jobs.map(job => 
        job.id === id ? { ...job, status: 'completed' } : job
      ));
    }, 2000);
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
        <div className={`rounded-lg p-4 mb-6 ${managerRunning ? 'bg-green-50 border border-green-200' : 'bg-[#E8E2DB]/30 border border-[#629FAD]/30'}`}>
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
              onClick={() => setManagerRunning(!managerRunning)}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                managerRunning 
                  ? 'bg-[#629FAD]/20 text-[#0C2C55] hover:bg-[#629FAD]/30' 
                  : 'bg-[#0C2C55] text-[#E8E2DB] hover:bg-[#0C2C55]/90'
              }`}
            >
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
        {filteredJobs.length === 0 ? (
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
                <thead className="bg-[#E8E2DB]/30 border-b border-[#629FAD]/30">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Sent</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Job Details</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Links</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Retry</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Fields</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-[#296374] uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#629FAD]/20">
                  {filteredJobs.map((job) => (
                    <tr key={job.id} className="hover:bg-[#E8E2DB]/20">
                      <td className="px-6 py-4">
                        <input
                          type="checkbox"
                          checked={job.sent}
                          onChange={() => toggleSent(job.id)}
                          className="w-4 h-4 text-[#0C2C55] rounded focus:ring-[#296374]"
                        />
                      </td>
                      <td className="px-6 py-4 text-sm text-[#296374] whitespace-nowrap">{job.date}</td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-[#0C2C55]">{job.title}</div>
                        <div className="text-sm text-[#296374]">{job.company}</div>
                        <div className="text-xs text-[#629FAD] mt-1">{job.source}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2">
                          <a
                            href={job.jobUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 text-[#296374] hover:bg-[#629FAD]/10 rounded transition-colors"
                            title="Job Description"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                          <a
                            href={job.applyUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 text-green-600 hover:bg-green-50 rounded transition-colors"
                            title="Apply Page"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        </div>
                      </td>
                      <td className="px-6 py-4">{getStatusBadge(job.status)}</td>
                      <td className="px-6 py-4 text-sm text-[#296374]">{job.retryCount}</td>
                      <td className="px-6 py-4 text-sm text-[#296374]">
                        <span className={job.filledFields === job.totalFields ? 'text-green-600 font-medium' : ''}>
                          {job.filledFields} / {job.totalFields}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-1">
                          <button
                            onClick={() => setSelectedJob(job)}
                            className="p-1.5 text-[#296374] hover:bg-[#629FAD]/10 rounded transition-colors"
                            title="View JSON"
                          >
                            <Code className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setPreviewJob(job)}
                            className="p-1.5 text-[#296374] hover:bg-[#629FAD]/10 rounded transition-colors"
                            title="Preview Resume"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            className="p-1.5 text-[#296374] hover:bg-[#629FAD]/10 rounded transition-colors"
                            title="Open Draft"
                          >
                            <FileText className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => rerunJob(job.id)}
                            className="p-1.5 text-green-600 hover:bg-green-50 rounded transition-colors"
                            title="Rerun"
                          >
                            <RotateCw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deleteJob(job.id)}
                            className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {selectedJob && (
        <JobJsonModal job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
      {showAddDialog && (
        <AddJobDialog 
          onClose={() => setShowAddDialog(false)}
          onAdd={(url) => {
            const newJob: Job = {
              id: Date.now().toString(),
              sent: false,
              date: new Date().toISOString().slice(0, 16).replace('T', ' '),
              title: 'Processing...',
              company: 'Unknown',
              source: 'Manual',
              jobUrl: url,
              applyUrl: url,
              status: 'running',
              retryCount: 0,
              filledFields: 0,
              totalFields: 15,
            };
            setJobs([newJob, ...jobs]);
            setShowAddDialog(false);
          }}
        />
      )}
      {previewJob && (
        <ResumePreviewPopup 
          job={{
            id: previewJob.id,
            title: previewJob.title,
            company: previewJob.company,
            jobDescription: `Position: ${previewJob.title}\nCompany: ${previewJob.company}\n\nWe are seeking a talented ${previewJob.title} to join our team. The ideal candidate will have extensive experience with modern web technologies including React, TypeScript, and Node.js.\n\nResponsibilities:\n- Develop and maintain high-quality web applications\n- Collaborate with cross-functional teams\n- Write clean, maintainable code\n- Participate in code reviews\n\nRequirements:\n- 5+ years of frontend development experience\n- Expert knowledge of React and TypeScript\n- Strong understanding of web performance optimization\n- Experience with CI/CD pipelines\n- Excellent communication skills`
          }} 
          onClose={() => setPreviewJob(null)} 
        />
      )}
    </div>
  );
}