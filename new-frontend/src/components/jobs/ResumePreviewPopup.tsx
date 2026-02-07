import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
    Clock,
    AlertCircle,
    Loader2,
    Copy,
    FileEdit,
    Save,
    Sparkles,
} from 'lucide-react';
import { toast } from "sonner";
import { API_URL } from '@/lib/env';
import { cn } from "@/lib/utils";

interface ResumeVersion {
    id: string;
    version_number: number;
    ats_score?: number;
    justification?: string;
    keywords_added?: string;
    changes_summary?: string;
    status: string;
    is_current: boolean;
    created_at: string;
}

interface ResumePreviewPopupProps {
    isOpen: boolean; // Using isOpen to match old prop name, will map to open in Sheet
    onClose: () => void;
    draftId: string;
    jobUrl: string;
}

export function ResumePreviewPopup({ isOpen, onClose, draftId }: ResumePreviewPopupProps) {
    const [versions, setVersions] = useState<ResumeVersion[]>([]);
    const [jobDetails, setJobDetails] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<'resume' | 'description'>('resume');
    const [loading, setLoading] = useState(true);
    const [refining, setRefining] = useState(false);
    const [refinementPrompt, setRefinementPrompt] = useState("");
    const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

    // NEW: Manual editing & Prompt extraction
    const [isManualEditing, setIsManualEditing] = useState(false);
    const [manualLatex, setManualLatex] = useState("");
    const [savingManual, setSavingManual] = useState(false);
    const [copyingPrompt, setCopyingPrompt] = useState(false);

    const fetchVersions = async () => {
        if (!draftId) return;
        try {
            const res = await axios.get(`${API_URL}/drafts/${draftId}/resume/versions`);
            const fetchedVersions: ResumeVersion[] = res.data;
            setVersions(fetchedVersions);

            if (fetchedVersions.length > 0) {
                // Determine which version to show in preview
                const currentSelected = fetchedVersions.find(v => v.id === selectedVersionId);

                // If nothing selected yet, or current selected is gone
                if (!selectedVersionId || !currentSelected) {
                    // 1. Try to find the version marked as is_current
                    const currentVersion = fetchedVersions.find(v => v.is_current);
                    if (currentVersion) {
                        setSelectedVersionId(currentVersion.id);
                    } else {
                        // 2. Fallback to newest completed
                        const completedVersions = fetchedVersions.filter(v => v.status === 'COMPLETED');
                        if (completedVersions.length > 0) {
                            setSelectedVersionId(completedVersions[0].id);
                        } else {
                            // 3. Absolute fallback to latest
                            setSelectedVersionId(fetchedVersions[0].id);
                        }
                    }
                }
                // Special case: if we have a selection but it's GENERATING, 
                // see if there's a COMPLETED one we should be showing instead
                else if (currentSelected.status === 'GENERATING') {
                    const completedVersions = fetchedVersions.filter(v => v.status === 'COMPLETED');
                    if (completedVersions.length > 0) {
                         // Only switch if the completed one is actually newer or if the user hasn't explicitly clicked the generating one
                         // For simplicity, let's just stick to the newest completed if current is generating
                        setSelectedVersionId(completedVersions[0].id);
                    }
                }
            }
        } catch (e) {
            console.error(e);
            toast.error("Failed to load resume versions");
        }
    };

    const fetchDraft = async () => {
        if (!draftId) return;
        try {
            const res = await axios.get(`${API_URL}/drafts/${draftId}`);
            setJobDetails(res.data.job_details);
        } catch (e) {
            console.error(e);
        }
    };

    const loadAll = async () => {
        setLoading(true);
        await Promise.all([fetchVersions(), fetchDraft()]);
        setLoading(false);
    };

    useEffect(() => {
        if (isOpen && draftId) {
            loadAll();
        }
    }, [isOpen, draftId]);

    // Polling if any version is generating
    useEffect(() => {
        let interval: ReturnType<typeof setInterval>;
        const needsPolling = versions.some(v => v.status === 'GENERATING');

        if (isOpen && needsPolling) {
            interval = setInterval(fetchVersions, 3000);
        }

        return () => {
             if (interval) clearInterval(interval);
        };
    }, [isOpen, versions]);

    const handleRefine = async () => {
        if (!refinementPrompt) return;
        setRefining(true);
        try {
            await axios.post(`${API_URL}/drafts/${draftId}/resume/versions`, {
                prompt: refinementPrompt
            });
            toast.success("New resume version is being generated...");
            setRefinementPrompt("");
            await fetchVersions();
            setViewMode('resume'); // Auto switch view mode anyway
        } catch (e) {
            console.error(e);
            toast.error("Failed to refine resume");
        } finally {
            setRefining(false);
        }
    };

    const handleSelectVersion = async (vId: string) => {
        try {
            await axios.post(`${API_URL}/drafts/${draftId}/resume/versions/${vId}/select`);
            toast.success("Resume version selected for submission");
            fetchVersions();
            setIsManualEditing(false);
        } catch (e) {
            console.error(e);
            toast.error("Failed to select version");
        }
    };

    const handleCopyPrompt = async () => {
        if (!selectedVersionId) return;
        setCopyingPrompt(true);
        try {
            const res = await axios.get(`${API_URL}/drafts/${draftId}/resume/versions/${selectedVersionId}/prompt`);
            await navigator.clipboard.writeText(res.data.prompt);
            toast.success("Prompt copied to clipboard!");
        } catch (e) {
             toast.error("Failed to copy prompt");
        } finally {
            setCopyingPrompt(false);
        }
    };

    const handleGoToChatGPT = () => {
        window.open("https://chatgpt.com", "_blank");
    };

    const handleStartManualEdit = async () => {
        if (!selectedVersionId) return;
        try {
            const res = await axios.get(`${API_URL}/drafts/${draftId}/resume/versions/${selectedVersionId}/tex`);
            setManualLatex(res.data.tex);
            setIsManualEditing(true);
        } catch (e) {
            toast.error("Failed to load LaTeX source");
        }
    };

    const handleSaveManualEdit = async () => {
        if (!manualLatex) return;
        setSavingManual(true);
        try {
            await axios.post(`${API_URL}/drafts/${draftId}/resume/versions/manual`, {
                latex: manualLatex
            });
            toast.success("New version created! Compiling PDF in background...");
            setIsManualEditing(false);
            // Refresh versions after a short delay
            setTimeout(fetchVersions, 1000);
        } catch (e) {
            toast.error("Failed to save manual edit");
        } finally {
            setSavingManual(false);
        }
    };

    const handleUseOriginal = async () => {
        try {
            const resp = await axios.post(`${API_URL}/drafts/${draftId}/resume/use_original`);
            toast.success("Original resume added to version history");
            fetchVersions();
            setSelectedVersionId(resp.data.id);
            setViewMode('resume');
        } catch (e: any) {
            toast.error(e.response?.data?.detail || "Failed to use original resume");
        }
    };

    // Helper for status badge
    const getStatusBadge = (status: string) => {
        const styles: Record<string, string> = {
            COMPLETED: "bg-green-100 text-green-700",
            GENERATING: "bg-blue-100 text-blue-700 animate-pulse",
            FAILED: "bg-red-100 text-red-700",
            ARCHIVED: "bg-gray-100 text-gray-700",
        };
        const style = styles[status] || styles.ARCHIVED;
        
        return (
            <Badge className={cn("border-none h-5 text-[10px] px-1.5 font-medium", style)}>
                {status}
            </Badge>
        );
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
            <div className="bg-white rounded-lg w-full max-w-[1400px] h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between p-4 px-6 border-b border-[#629FAD]/30 bg-white shrink-0">
                    <div>
                        <h2 className="text-xl font-semibold text-[#0C2C55]">Resume Preview</h2>
                        <p className="text-sm text-[#296374] mt-1">Manage versions and refine content</p>
                    </div>
                    <Button 
                        variant="ghost" 
                        size="icon" 
                        onClick={onClose}
                        className="text-[#629FAD] hover:text-[#0C2C55] hover:bg-[#E8E2DB]/50 rounded-lg"
                    >
                         <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-x"><path d="M18 6 6 18"/><path d="m6 6 18 18"/></svg>
                    </Button>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    {/* Left Sidebar: Version History */}
                    <div className="w-80 border-r border-[#629FAD]/30 bg-[#E8E2DB]/20 flex flex-col shrink-0">
                        <div className="p-4 border-b border-[#629FAD]/20 flex items-center justify-between bg-[#E8E2DB]/30">
                            <h3 className="font-semibold text-[#0C2C55] flex items-center gap-2">
                                <Clock className="h-4 w-4" /> History
                            </h3>
                            <Button
                                variant="outline"
                                size="sm"
                                className="h-7 text-[10px] px-2 bg-white border-[#629FAD]/30 text-[#0C2C55] hover:bg-[#E8E2DB]"
                                onClick={handleUseOriginal}
                            >
                                Use Original
                            </Button>
                        </div>
                        
                        <ScrollArea className="flex-1">
                            <div className="p-3 space-y-3">
                                {versions.map((v) => (
                                    <div
                                        key={v.id}
                                        onClick={() => setSelectedVersionId(v.id)}
                                        className={cn(
                                            "p-3 rounded-lg border-2 cursor-pointer transition-all hover:shadow-sm",
                                            selectedVersionId === v.id
                                                ? "border-[#0C2C55] bg-[#0C2C55]/5"
                                                : "border-[#629FAD]/20 bg-white hover:border-[#629FAD]/50"
                                        )}
                                    >
                                        <div className="flex items-start justify-between mb-2">
                                            <div className="space-y-1">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-semibold text-sm text-[#0C2C55]">v{v.version_number}</span>
                                                    {v.is_current && <Badge className="bg-green-600 text-[9px] h-4 px-1">Active</Badge>} 
                                                    {getStatusBadge(v.status)}
                                                </div>
                                                <div className="text-[10px] text-[#629FAD]">
                                                    {new Date(v.created_at).toLocaleString()}
                                                </div>
                                            </div>
                                            {v.ats_score && (
                                                <div className={cn(
                                                    "font-bold text-sm",
                                                    v.ats_score > 80 ? "text-green-600" : "text-amber-600"
                                                )}>
                                                    {v.ats_score}
                                                </div>
                                            )}
                                        </div>

                                        {v.changes_summary && (
                                            <p className="text-xs text-[#296374] line-clamp-2 my-2 italic">
                                                "{v.changes_summary}"
                                            </p>
                                        )}

                                        {v.keywords_added && v.keywords_added.length > 0 && (
                                            <div className="flex flex-wrap gap-1 mt-2">
                                                {v.keywords_added.split(',').slice(0, 3).map((kw, i) => (
                                                    <span key={i} className="text-[9px] px-1.5 py-0.5 bg-[#629FAD]/10 text-[#296374] rounded-full border border-[#629FAD]/20">
                                                        {kw.trim()}
                                                    </span>
                                                ))}
                                                {v.keywords_added.split(',').length > 3 && (
                                                    <span className="text-[9px] text-[#629FAD] px-1">...</span>
                                                )}
                                            </div>
                                        )}

                                        {selectedVersionId === v.id && !v.is_current && v.status === 'COMPLETED' && (
                                           <Button
                                                size="sm"
                                                variant="default"
                                                className="w-full mt-3 h-7 text-xs bg-[#0C2C55] hover:bg-[#0C2C55]/90"
                                                onClick={(e) => { e.stopPropagation(); handleSelectVersion(v.id); }}
                                            >
                                                Use This Version
                                            </Button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    </div>

                    {/* Main Content Area */}
                    <div className="flex-1 flex flex-col bg-[#F8F9FA] min-w-0">
                        {/* Toolbar */}
                        <div className="flex items-center justify-between p-3 border-b border-[#629FAD]/20 bg-white">
                            <div className="flex gap-2">
                                <div className="bg-[#E8E2DB]/30 p-1 rounded-lg flex gap-1">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setViewMode('resume')}
                                        className={cn(
                                            "h-8 text-xs font-medium transition-all",
                                            viewMode === 'resume' 
                                                ? "bg-[#0C2C55] text-white shadow-sm hover:bg-[#0C2C55]/90" 
                                                : "text-[#296374] hover:bg-[#E8E2DB]/50"
                                        )}
                                    >
                                        Resume Preview
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setViewMode('description')}
                                        className={cn(
                                            "h-8 text-xs font-medium transition-all",
                                            viewMode === 'description' 
                                                ? "bg-[#0C2C55] text-white shadow-sm hover:bg-[#0C2C55]/90" 
                                                : "text-[#296374] hover:bg-[#E8E2DB]/50"
                                        )}
                                    >
                                        Job Description
                                    </Button>
                                </div>
                            </div>

                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleCopyPrompt}
                                    disabled={copyingPrompt}
                                    className="h-8 text-xs gap-1.5 border-[#629FAD]/30 text-[#0C2C55] hover:bg-[#F8F9FA]"
                                >
                                    {copyingPrompt ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Copy className="h-3.5 w-3.5" />}
                                    Copy Prompt
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleGoToChatGPT}
                                    className="h-8 text-xs gap-1.5 border-[#629FAD]/30 text-[#0C2C55] hover:bg-[#F8F9FA]"
                                >
                                    <Sparkles className="h-3.5 w-3.5" />
                                    ChatGPT
                                </Button>
                                <Button
                                    variant={isManualEditing ? "default" : "outline"}
                                    size="sm"
                                    onClick={() => {
                                        if (isManualEditing) {
                                            setIsManualEditing(false);
                                        } else {
                                            handleStartManualEdit();
                                        }
                                    }}
                                    className={cn(
                                        "h-8 text-xs gap-1.5 border-[#629FAD]/30 transition-colors",
                                        isManualEditing ? "bg-[#0C2C55] text-white" : "text-[#0C2C55] hover:bg-[#F8F9FA]"
                                    )}
                                >
                                    <FileEdit className="h-3.5 w-3.5" />
                                    {isManualEditing ? "Exit Edit" : "Manual Edit"}
                                </Button>
                            </div>
                        </div>

                        {/* Content Viewer */}
                        <div className="flex-1 overflow-hidden p-6 bg-[#E8E2DB]/10 relative">
                            {viewMode === 'resume' ? (
                                isManualEditing ? (
                                    <div className="bg-white rounded-xl border border-[#629FAD]/30 shadow-sm h-full flex flex-col overflow-hidden">
                                        <div className="flex items-center justify-between p-3 border-b border-[#629FAD]/20 bg-[#F8F9FA]">
                                            <div className="flex items-center gap-2">
                                                <code className="text-xs text-[#629FAD] bg-[#E8E2DB]/30 px-2 py-1 rounded">source.tex</code>
                                            </div>
                                            <Button 
                                                size="sm" 
                                                onClick={handleSaveManualEdit} 
                                                disabled={savingManual} 
                                                className="h-7 text-xs bg-[#0C2C55] hover:bg-[#0C2C55]/90"
                                            >
                                                {savingManual ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Save className="h-3 w-3 mr-1" />}
                                                Save & Compile
                                            </Button>
                                        </div>
                                        <textarea
                                            className="flex-1 p-4 font-mono text-xs leading-relaxed resize-none focus:outline-none text-[#0C2C55] selection:bg-[#629FAD]/20"
                                            value={manualLatex}
                                            onChange={(e) => setManualLatex(e.target.value)}
                                            spellCheck={false}
                                        />
                                    </div>
                                ) : (
                                    <div className="h-full bg-white rounded-xl shadow-lg border border-[#629FAD]/10 overflow-hidden relative group">
                                         {selectedVersionId ? (
                                            <iframe
                                                src={`${API_URL}/drafts/${draftId}/resume/preview?version_id=${selectedVersionId}&t=${new Date().getTime()}`}
                                                className="w-full h-full border-none"
                                                title="Resume Preview"
                                            />
                                        ) : (
                                            <div className="flex flex-col items-center justify-center h-full text-[#629FAD] gap-3">
                                                {loading ? (
                                                    <>
                                                        <Loader2 className="h-8 w-8 animate-spin" />
                                                        <span className="text-sm">Loading preview...</span>
                                                    </>
                                                ) : (
                                                    <span className="text-sm">Select a version to preview</span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )
                            ) : (
                                <div className="h-full bg-white rounded-xl border border-[#629FAD]/20 shadow-sm overflow-hidden flex flex-col">
                                    <div className="p-6 overflow-y-auto custom-scrollbar">
                                        <h3 className="text-lg font-bold text-[#0C2C55] mb-4 sticky top-0 bg-white pb-2 border-b border-[#E8E2DB]">Job Description</h3>
                                        <div className="prose prose-sm max-w-none text-[#296374]">
                                            {jobDetails ? (
                                                <div className="whitespace-pre-wrap leading-relaxed">
                                                    {jobDetails}
                                                </div>
                                            ) : (
                                                <div className="flex flex-col items-center justify-center h-40 italic opacity-60">
                                                    <AlertCircle className="h-8 w-8 mb-2" />
                                                    No job description available
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Bottom Refinement Bar */}
                        <div className="p-4 bg-white border-t border-[#629FAD]/20 shrink-0">
                            <div className="flex gap-3 max-w-5xl mx-auto">
                                <div className="flex-1 relative">
                                    <Textarea
                                        placeholder="Enter instructions to refine your resume (e.g., 'Emphasize my cloud experience', 'Make it one page')..."
                                        className="min-h-[50px] max-h-[120px] pr-24 resize-none border-[#629FAD]/30 focus-visible:ring-[#0C2C55] text-sm"
                                        value={refinementPrompt}
                                        onChange={(e) => setRefinementPrompt(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault();
                                                handleRefine();
                                            }
                                        }}
                                    />
                                    <div className="absolute right-2 bottom-2 text-[10px] text-muted-foreground bg-white/80 px-1 rounded">
                                        Press Enter to refine
                                    </div>
                                </div>
                                <Button
                                    className="h-auto bg-[#296374] hover:bg-[#0C2C55] text-white px-6 transition-all"
                                    disabled={refining || !refinementPrompt}
                                    onClick={handleRefine}
                                >
                                    {refining ? (
                                        <Loader2 className="h-5 w-5 animate-spin" />
                                    ) : (
                                        <div className="flex flex-col items-center">
                                            <Sparkles className="h-5 w-5 mb-0.5" />
                                            <span className="text-[10px] font-medium leading-none">REFINE</span>
                                        </div>
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
