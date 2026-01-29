import { useState } from 'react';
import { X, Copy, ExternalLink, Code, FileText, CheckCircle, XCircle, Clock, Sparkles } from 'lucide-react';

// Using a simplified interface for now to support the UI
interface ResumeVersion {
  id: string;
  timestamp: string;
  atsScore: number;
  status: 'current' | 'generating' | 'failed' | 'archived';
  changesSummary: string;
  keywordsAdded: string[];
  pdfUrl: string;
  latexSource: string;
  promptUsed: string;
}

interface ResumePreviewPopupProps {
  job: {
    id: string;
    title: string;
    company: string;
    jobDescription: string;
  };
  onClose: () => void;
  // Intended for future real data integration
  draftId?: string;
  jobUrl?: string;
}

export function ResumePreviewPopup({ job, onClose }: ResumePreviewPopupProps) {
  const [viewMode, setViewMode] = useState<'resume' | 'job'>('resume');
  const [editMode, setEditMode] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState('1');
  const [refinementInstructions, setRefinementInstructions] = useState('');
  const [latexCode, setLatexCode] = useState('');

  // Mock data preserved from Figma UI for now - will need Backend integration
  const [versions, setVersions] = useState<ResumeVersion[]>([
    {
      id: '1',
      timestamp: new Date().toISOString(),
      atsScore: 92,
      status: 'current',
      changesSummary: 'Initial tailored version',
      keywordsAdded: ['React', 'TypeScript'],
      pdfUrl: '', // Will need actual PDF URL for iframe
      latexSource: '\\documentclass{article}\n\\begin{document}\nResume Content\n\\end{document}',
      promptUsed: 'Tailor resume...'
    }
  ]);

  const currentVersion = versions.find(v => v.id === selectedVersion) || versions[0];

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(currentVersion.promptUsed);
    } catch {
      // Fallback ignored for brevity
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      current: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
      generating: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Clock },
      failed: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
      archived: { bg: 'bg-gray-100', text: 'text-gray-700', icon: FileText },
    };
    const config = styles[status as keyof typeof styles] || styles.archived;
    const Icon = config.icon;
    return (
      <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${config.bg} ${config.text}`}>
        <Icon className="w-3 h-3" />
        <span className="text-xs font-medium capitalize">{status}</span>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
      <div className="bg-white rounded-lg w-full max-w-[1400px] h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#629FAD]/30">
          <div>
            <h2 className="text-xl font-semibold text-[#0C2C55]">Resume Preview</h2>
            <p className="text-sm text-[#296374] mt-1">{job.title} at {job.company}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-[#629FAD] hover:text-[#0C2C55] rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Version History Sidebar */}
          <div className="w-80 border-r border-[#629FAD]/30 overflow-y-auto p-4 bg-[#E8E2DB]/20">
            <h3 className="font-semibold text-[#0C2C55] mb-4">Version History</h3>
            <div className="space-y-3">
              {versions.map((version) => (
                <div
                  key={version.id}
                  onClick={() => setSelectedVersion(version.id)}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedVersion === version.id
                      ? 'border-[#0C2C55] bg-[#0C2C55]/10'
                      : 'border-[#629FAD]/30 bg-white hover:border-[#296374]'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {getStatusBadge(version.status)}
                    <span className="text-xs text-[#629FAD]">
                        {new Date(version.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-xs text-[#0C2C55] mb-2">{version.changesSummary}</p>
                   {version.status !== 'current' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            // Logic to set as current would go here
                          }}
                          className="w-full mt-2 px-3 py-1.5 text-xs bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
                        >
                          Use This Version
                        </button>
                    )}
                </div>
              ))}
            </div>
          </div>

          {/* Center Preview Area */}
          <div className="flex-1 flex flex-col">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-4 border-b border-[#629FAD]/30 bg-[#E8E2DB]/20">
              <div className="flex gap-2">
                <button
                  onClick={() => setViewMode('resume')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    viewMode === 'resume'
                      ? 'bg-[#0C2C55] text-[#E8E2DB]'
                      : 'bg-white text-[#0C2C55] border border-[#629FAD]/30 hover:bg-[#E8E2DB]/50'
                  }`}
                >
                  Resume Preview
                </button>
                <button
                  onClick={() => setViewMode('job')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    viewMode === 'job'
                      ? 'bg-[#0C2C55] text-[#E8E2DB]'
                      : 'bg-white text-[#0C2C55] border border-[#629FAD]/30 hover:bg-[#E8E2DB]/50'
                  }`}
                >
                  Job Description
                </button>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={copyPrompt}
                  className="flex items-center gap-2 px-3 py-2 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
                >
                  <Copy className="w-4 h-4" />
                  Prompt
                </button>
                <button
                  onClick={() => window.open('https://chat.openai.com', '_blank')}
                  className="flex items-center gap-2 px-3 py-2 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  ChatGPT
                </button>
                <button
                  onClick={() => {
                        setEditMode(!editMode);
                        if (!editMode) setLatexCode(currentVersion.latexSource);
                  }}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                    editMode
                      ? 'bg-[#0C2C55] text-[#E8E2DB]'
                      : 'bg-white text-[#0C2C55] border border-[#629FAD]/30 hover:bg-[#E8E2DB]/50'
                  }`}
                >
                  <Code className="w-4 h-4" />
                  {editMode ? 'View Mode' : 'Manual Edit'}
                </button>
              </div>
            </div>

            {/* Preview Content */}
            <div className="flex-1 overflow-auto p-6 bg-[#E8E2DB]/10">
              {viewMode === 'resume' ? (
                editMode ? (
                  <div className="bg-white p-4 rounded-lg shadow h-full flex flex-col">
                      <textarea 
                        className="flex-1 font-mono text-sm p-2 bg-slate-50 border rounded resize-none focus:outline-none focus:ring-2 focus:ring-[#296374]"
                        value={latexCode}
                        onChange={(e) => setLatexCode(e.target.value)}
                      />
                  </div>
                ) : (
                  <div className="bg-white rounded-lg shadow-lg h-full flex items-center justify-center">
                    {currentVersion.pdfUrl ? (
                         <iframe src={currentVersion.pdfUrl} className="w-full h-full rounded-lg" />
                    ) : (
                        <div className="text-center">
                            <FileText className="w-16 h-16 text-[#629FAD] mx-auto mb-4" />
                            <p className="text-[#296374]">PDF Preview Not Available (Mock)</p>
                        </div>
                    )}
                  </div>
                )
              ) : (
                <div className="bg-white rounded-lg border border-[#629FAD]/30 p-6 h-full overflow-auto shadow-sm prose max-w-none">
                  <p className="whitespace-pre-wrap">{job.jobDescription}</p>
                </div>
              )}
            </div>

            {/* AI Refinement (Simplified) */}
             <div className="p-4 border-t border-[#629FAD]/30 bg-white">
              <div className="flex gap-3">
                 <input 
                    className="flex-1 px-4 py-2 border border-[#629FAD]/30 rounded-lg"
                    placeholder="Refinement instructions..."
                    value={refinementInstructions}
                    onChange={(e) => setRefinementInstructions(e.target.value)}
                 />
                 <button className="px-6 py-2 bg-[#296374] text-white rounded-lg hover:bg-[#0C2C55]">
                    <Sparkles className="w-4 h-4 inline mr-2" />
                    Refine
                 </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
