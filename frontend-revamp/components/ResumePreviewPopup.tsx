import { useState } from 'react';
import { X, Copy, ExternalLink, Code, FileText, CheckCircle, XCircle, Clock, Sparkles } from 'lucide-react';

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
}

export function ResumePreviewPopup({ job, onClose }: ResumePreviewPopupProps) {
  const [viewMode, setViewMode] = useState<'resume' | 'job'>('resume');
  const [editMode, setEditMode] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState('1');
  const [refinementInstructions, setRefinementInstructions] = useState('');
  const [latexCode, setLatexCode] = useState('');

  const [versions, setVersions] = useState<ResumeVersion[]>([
    {
      id: '1',
      timestamp: '2026-01-27 14:30',
      atsScore: 92,
      status: 'current',
      changesSummary: 'Initial tailored version - emphasized React and TypeScript experience, added relevant keywords from job description',
      keywordsAdded: ['React', 'TypeScript', 'Agile', 'CI/CD'],
      pdfUrl: 'https://example.com/resume-v1.pdf',
      latexSource: '\\documentclass{article}\n\\begin{document}\n% Resume content\n\\end{document}',
      promptUsed: 'Tailor this resume for a Senior Frontend Developer role focusing on React and TypeScript...'
    },
    {
      id: '2',
      timestamp: '2026-01-27 13:15',
      atsScore: 85,
      status: 'archived',
      changesSummary: 'Second iteration - strengthened leadership experience, reordered projects section',
      keywordsAdded: ['Team Lead', 'Mentoring', 'Code Review'],
      pdfUrl: 'https://example.com/resume-v2.pdf',
      latexSource: '\\documentclass{article}\n\\begin{document}\n% Resume v2\n\\end{document}',
      promptUsed: 'Emphasize leadership and team collaboration aspects...'
    },
    {
      id: '3',
      timestamp: '2026-01-27 12:00',
      atsScore: 78,
      status: 'archived',
      changesSummary: 'First draft - basic keyword matching',
      keywordsAdded: ['JavaScript', 'Frontend'],
      pdfUrl: 'https://example.com/resume-v3.pdf',
      latexSource: '\\documentclass{article}\n\\begin{document}\n% Resume v3\n\\end{document}',
      promptUsed: 'Initial tailoring prompt...'
    }
  ]);

  const currentVersion = versions.find(v => v.id === selectedVersion) || versions[0];

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(currentVersion.promptUsed);
      // Could add a toast notification here
    } catch (err) {
      // Fallback: create a temporary textarea to copy
      const textarea = document.createElement('textarea');
      textarea.value = currentVersion.promptUsed;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
      } catch (e) {
        console.error('Failed to copy text:', e);
      }
      document.body.removeChild(textarea);
    }
  };

  const openChatGPT = () => {
    window.open('https://chat.openai.com', '_blank');
  };

  const toggleEditMode = () => {
    if (!editMode) {
      setLatexCode(currentVersion.latexSource);
    }
    setEditMode(!editMode);
  };

  const saveAndCompile = () => {
    console.log('Compiling LaTeX:', latexCode);
    // In real app, would send to backend to compile
    setEditMode(false);
  };

  const refineResume = () => {
    if (!refinementInstructions.trim()) return;
    
    const newVersion: ResumeVersion = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString().slice(0, 16).replace('T', ' '),
      atsScore: 0,
      status: 'generating',
      changesSummary: refinementInstructions,
      keywordsAdded: [],
      pdfUrl: '',
      latexSource: '',
      promptUsed: `Refine based on: ${refinementInstructions}`
    };
    
    setVersions([newVersion, ...versions]);
    setSelectedVersion(newVersion.id);
    setRefinementInstructions('');
    
    // Simulate generation
    setTimeout(() => {
      setVersions(prev => prev.map(v => 
        v.id === newVersion.id 
          ? { ...v, status: 'current', atsScore: Math.floor(Math.random() * 15) + 85 }
          : { ...v, status: v.status === 'current' ? 'archived' : v.status }
      ));
    }, 2000);
  };

  const handleApplyVersion = (versionId: string) => {
    setVersions(versions.map(v => ({
      ...v,
      status: v.id === versionId ? 'current' : (v.status === 'current' ? 'archived' : v.status)
    })));
    setSelectedVersion(versionId);
  };

  const handleUseOriginal = () => {
    console.log('Reverting to original uploaded resume');
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      current: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
      generating: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Clock },
      failed: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
      archived: { bg: 'bg-gray-100', text: 'text-gray-700', icon: FileText },
    };
    const config = styles[status as keyof typeof styles];
    const Icon = config.icon;
    return (
      <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${config.bg} ${config.text}`}>
        <Icon className="w-3 h-3" />
        <span className="text-xs font-medium capitalize">{status}</span>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
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
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-[#0C2C55]">Version History</h3>
              <button
                onClick={handleUseOriginal}
                className="text-xs px-3 py-1.5 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
                title="Use Original"
              >
                Use Original
              </button>
            </div>
            
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
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusBadge(version.status)}
                        {version.status !== 'generating' && (
                          <span className="text-xs text-[#629FAD]">{version.timestamp}</span>
                        )}
                      </div>
                      {version.status !== 'generating' && (
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs font-medium text-[#296374]">ATS Score:</span>
                          <span className={`text-sm font-bold ${
                            version.atsScore >= 90 ? 'text-green-600' : 
                            version.atsScore >= 80 ? 'text-yellow-600' : 'text-red-600'
                          }`}>
                            {version.atsScore}/100
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {version.status === 'generating' ? (
                    <div className="flex items-center gap-2 text-[#296374]">
                      <div className="w-4 h-4 border-2 border-[#296374] border-t-transparent rounded-full animate-spin" />
                      <span className="text-sm">Generating...</span>
                    </div>
                  ) : (
                    <>
                      <p className="text-xs text-[#0C2C55] mb-3 line-clamp-3">
                        {version.changesSummary}
                      </p>
                      
                      {version.keywordsAdded.length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs font-medium text-[#296374] mb-1">Keywords Added:</p>
                          <div className="flex flex-wrap gap-1">
                            {version.keywordsAdded.map((keyword, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 bg-[#629FAD]/20 text-[#296374] text-xs rounded-full"
                              >
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {version.status !== 'current' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleApplyVersion(version.id);
                          }}
                          className="w-full mt-2 px-3 py-1.5 text-xs bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
                        >
                          Use This Version
                        </button>
                      )}
                    </>
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
                  title="Copy AI Prompt"
                >
                  <Copy className="w-4 h-4" />
                  Copy Prompt
                </button>
                <button
                  onClick={openChatGPT}
                  className="flex items-center gap-2 px-3 py-2 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
                  title="Open ChatGPT"
                >
                  <ExternalLink className="w-4 h-4" />
                  ChatGPT
                </button>
                <button
                  onClick={toggleEditMode}
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
                  <div className="bg-white rounded-lg border border-[#629FAD]/30 h-full flex flex-col shadow-sm">
                    <div className="flex items-center justify-between p-4 border-b border-[#629FAD]/30">
                      <h3 className="font-semibold text-[#0C2C55]">LaTeX Source Code</h3>
                      <button
                        onClick={saveAndCompile}
                        className="px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
                      >
                        Save & Compile
                      </button>
                    </div>
                    <textarea
                      value={latexCode}
                      onChange={(e) => setLatexCode(e.target.value)}
                      className="flex-1 p-4 font-mono text-sm text-[#0C2C55] focus:outline-none resize-none"
                    />
                  </div>
                ) : (
                  <div className="bg-white rounded-lg shadow-lg h-full">
                    <iframe
                      src={currentVersion.pdfUrl}
                      className="w-full h-full rounded-lg"
                      title="Resume Preview"
                    />
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <FileText className="w-16 h-16 text-[#629FAD] mx-auto mb-4" />
                        <p className="text-[#296374]">Resume preview would appear here</p>
                        <p className="text-sm text-[#629FAD] mt-2">ATS Score: {currentVersion.atsScore}/100</p>
                      </div>
                    </div>
                  </div>
                )
              ) : (
                <div className="bg-white rounded-lg border border-[#629FAD]/30 p-6 h-full overflow-auto shadow-sm">
                  <h3 className="text-lg font-semibold text-[#0C2C55] mb-4">Job Description</h3>
                  <div className="prose prose-sm max-w-none">
                    <p className="text-[#0C2C55] whitespace-pre-wrap">
                      {job.jobDescription || `Position: ${job.title}\\nCompany: ${job.company}\\n\\nWe are seeking a talented ${job.title} to join our team. The ideal candidate will have extensive experience with modern web technologies including React, TypeScript, and Node.js.\\n\\nResponsibilities:\\n- Develop and maintain high-quality web applications\\n- Collaborate with cross-functional teams\\n- Write clean, maintainable code\\n- Participate in code reviews\\n\\nRequirements:\\n- 5+ years of frontend development experience\\n- Expert knowledge of React and TypeScript\\n- Strong understanding of web performance optimization\\n- Experience with CI/CD pipelines\\n- Excellent communication skills`}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* AI Refinement Control */}
            <div className="p-4 border-t border-[#629FAD]/30 bg-white">
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-[#0C2C55] mb-2">
                    AI Refinement Instructions
                  </label>
                  <textarea
                    value={refinementInstructions}
                    onChange={(e) => setRefinementInstructions(e.target.value)}
                    placeholder="e.g., Make the summary more concise, Emphasize my Python experience, Add more quantifiable achievements..."
                    rows={2}
                    className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374] resize-none"
                  />
                </div>
                <button
                  onClick={refineResume}
                  disabled={!refinementInstructions.trim()}
                  className="flex items-center gap-2 px-6 py-2 bg-[#296374] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55] disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-7"
                >
                  <Sparkles className="w-4 h-4" />
                  Refine Resume
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}