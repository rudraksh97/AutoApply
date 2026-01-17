"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetDescription,
    SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RefreshCw, Check, Clock, TrendingUp, AlertCircle, Loader2, Copy, FileEdit, Save, Sparkles, ExternalLink, Download } from 'lucide-react';
import { toast } from "sonner";

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
    isOpen: boolean;
    onClose: () => void;
    draftId: string;
    jobUrl: string;
}

export function ResumePreviewPopup({ isOpen, onClose, draftId, jobUrl }: ResumePreviewPopupProps) {
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
    const [versionLoading, setVersionLoading] = useState(false);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchVersions = async () => {
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
        let interval: NodeJS.Timeout;
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
            const res = await axios.post(`${API_URL}/drafts/${draftId}/resume/versions`, {
                prompt: refinementPrompt
            });
            toast.success("New resume version is being generated...");
            setRefinementPrompt("");
            await fetchVersions();
            // Don't setSelectedVersionId(res.data.id) immediately if it's GENERATING
            // The polling/fetchVersions logic will handle the switch when a completed one exists
            // or we can explicitly wait for it to be COMPLETED before switching.
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

    const currentVersion = versions.find(v => v.id === selectedVersionId);

    return (
        <Sheet open={isOpen} onOpenChange={onClose}>
            <SheetContent side="right" className="sm:max-w-4xl w-[90vw] p-0 flex flex-col">
                <SheetHeader className="p-6 border-b">
                    <div className="flex items-center justify-between">
                        <div>
                            <SheetTitle>Resume Preview & Refinement</SheetTitle>
                            <SheetDescription>
                                Preview your tailored resume and its job description.
                            </SheetDescription>
                        </div>
                        {currentVersion && (
                            <div className="flex items-center gap-2">
                                <Badge variant="secondary" className="h-8 px-3 text-sm font-semibold flex items-center gap-1.5">
                                    <TrendingUp className="h-3.5 w-3.5" />
                                    ATS Score: {currentVersion.ats_score || 'N/A'}/100
                                </Badge>
                            </div>
                        )}
                    </div>
                </SheetHeader>

                <div className="flex-1 flex overflow-hidden">
                    {/* Left: PDF Preview or JD */}
                    <div className="flex-[3] bg-muted relative border-r flex flex-col">
                        <div className="bg-white border-b px-4 h-11 flex items-center justify-between shrink-0">
                            <div className="flex gap-1 p-1 bg-muted rounded-md h-9">
                                <Button
                                    variant={viewMode === 'resume' ? 'default' : 'ghost'}
                                    size="sm"
                                    className="h-7 text-xs"
                                    onClick={() => setViewMode('resume')}
                                >
                                    Resume Preview
                                </Button>
                                <Button
                                    variant={viewMode === 'description' ? 'default' : 'ghost'}
                                    size="sm"
                                    className="h-7 text-xs"
                                    onClick={() => setViewMode('description')}
                                >
                                    Job Description
                                </Button>
                            </div>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleCopyPrompt}
                                    disabled={copyingPrompt}
                                    className="h-7 text-[10px] gap-1 px-2"
                                >
                                    {copyingPrompt ? <Loader2 className="h-3 w-3 animate-spin" /> : <Copy className="h-3 w-3" />}
                                    Copy Prompt
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleGoToChatGPT}
                                    className="h-7 text-[10px] gap-1 px-2"
                                >
                                    <Sparkles className="h-3 w-3" />
                                    ChatGPT
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleStartManualEdit}
                                    className="h-7 text-[10px] gap-1 px-2"
                                >
                                    <FileEdit className="h-3 w-3" />
                                    Manual Edit
                                </Button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-hidden relative">
                            {viewMode === 'resume' ? (
                                isManualEditing ? (
                                    <div className="flex-1 flex flex-col h-full bg-slate-950">
                                        <div className="flex items-center justify-between p-2 bg-slate-900 border-b border-slate-800">
                                            <span className="text-[10px] text-slate-400 font-mono">resume_source.tex</span>
                                            <div className="flex gap-2">
                                                <Button size="sm" variant="ghost" className="h-6 text-[10px] text-slate-300 hover:text-white" onClick={() => setIsManualEditing(false)}>Cancel</Button>
                                                <Button size="sm" onClick={handleSaveManualEdit} disabled={savingManual} className="h-6 text-[10px] bg-blue-600 hover:bg-blue-700">
                                                    {savingManual ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Save className="h-3 w-3 mr-1" />}
                                                    Save & Compile
                                                </Button>
                                            </div>
                                        </div>
                                        <textarea
                                            className="w-full flex-1 p-4 font-mono text-[11px] resize-none focus:outline-none bg-slate-950 text-slate-200 border-none"
                                            value={manualLatex}
                                            onChange={(e) => setManualLatex(e.target.value)}
                                            spellCheck={false}
                                        />
                                    </div>
                                ) : (
                                    selectedVersionId ? (
                                        <iframe
                                            src={`${API_URL}/drafts/${draftId}/resume/preview?version_id=${selectedVersionId}&t=${new Date().getTime()}`}
                                            className="w-full h-full border-none"
                                            title="Resume Preview"
                                        />
                                    ) : (
                                        <div className="flex items-center justify-center h-full">
                                            {loading ? <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /> : "No resume preview available"}
                                        </div>
                                    )
                                )
                            ) : (
                                <ScrollArea className="h-full bg-white">
                                    <div className="p-8 prose prose-sm max-w-none">
                                        <h2 className="text-xl font-bold mb-4">Job Description</h2>
                                        {jobDetails ? (
                                            <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                                                {jobDetails}
                                            </div>
                                        ) : (
                                            <div className="flex flex-col items-center justify-center h-40 text-muted-foreground italic">
                                                <AlertCircle className="h-8 w-8 mb-2 opacity-50" />
                                                No job description details captured.
                                            </div>
                                        )}
                                    </div>
                                </ScrollArea>
                            )}
                        </div>
                    </div>

                    {/* Right: Versions & Refinement */}
                    <div className="flex-[2] flex flex-col min-w-[320px]">
                        <ScrollArea className="flex-1">
                            <div className="p-6 space-y-6">
                                <div>
                                    <div className="flex items-center justify-between mb-3">
                                        <h3 className="text-sm font-semibold flex items-center gap-2">
                                            <Clock className="h-4 w-4" />
                                            Version History
                                        </h3>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="h-7 text-[10px] px-2"
                                            onClick={handleUseOriginal}
                                        >
                                            Use Original
                                        </Button>
                                    </div>
                                    <div className="space-y-3">
                                        {versions.map((v) => (
                                            <div
                                                key={v.id}
                                                className={cn(
                                                    "p-3 rounded-lg border cursor-pointer transition-all",
                                                    selectedVersionId === v.id ? "border-primary bg-primary/5 ring-1 ring-primary" : "hover:border-primary/50"
                                                )}
                                                onClick={() => setSelectedVersionId(v.id)}
                                            >
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="font-medium text-sm">Version {v.version_number}</span>
                                                    {v.is_current && (
                                                        <Badge className="bg-green-100 text-green-700 hover:bg-green-100 border-none h-5 text-[10px] px-1.5">
                                                            CURRENT
                                                        </Badge>
                                                    )}
                                                    {v.status === 'GENERATING' && (
                                                        <Badge className="bg-yellow-100 text-yellow-700 animate-pulse border-none h-5 text-[10px] px-1.5 ml-1">
                                                            Generating...
                                                        </Badge>
                                                    )}
                                                    {v.status === 'FAILED' && (
                                                        <Badge className="bg-red-100 text-red-700 border-none h-5 text-[10px] px-1.5 ml-1">
                                                            Failed
                                                        </Badge>
                                                    )}
                                                </div>
                                                <div className="flex items-center justify-between text-xs text-muted-foreground">
                                                    <span>Score: {v.status === 'GENERATING' ? '...' : (v.ats_score || 'N/A')}</span>
                                                    <span>{new Date(v.created_at).toLocaleDateString()}</span>
                                                </div>
                                                {v.changes_summary && (
                                                    <p className="text-[11px] mt-2 italic text-muted-foreground line-clamp-2">
                                                        "{v.changes_summary}"
                                                    </p>
                                                )}
                                                {v.keywords_added && (
                                                    <div className="flex flex-wrap gap-1 mt-2">
                                                        {v.keywords_added.split(',').map((kw, i) => kw.trim() && (
                                                            <Badge key={i} variant="outline" className="text-[9px] px-1 h-3.5 bg-blue-50/50 text-blue-700 border-blue-200">
                                                                {kw.trim()}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                )}
                                                {selectedVersionId === v.id && !v.is_current && (
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        className="w-full mt-3 h-7 text-xs"
                                                        onClick={(e) => { e.stopPropagation(); handleSelectVersion(v.id); }}
                                                    >
                                                        Use this version
                                                    </Button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <Separator />

                                <div>
                                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                                        <RefreshCw className="h-4 w-4" />
                                        Refinement Instructions
                                    </h3>
                                    <div className="space-y-3">
                                        <Textarea
                                            placeholder="Example: Add more emphasis on my AWS and Kubernetes experience. Make the summary more concise."
                                            className="min-h-[120px] text-sm resize-none"
                                            value={refinementPrompt}
                                            onChange={(e) => setRefinementPrompt(e.target.value)}
                                        />
                                        <Button
                                            className="w-full"
                                            disabled={refining || !refinementPrompt}
                                            onClick={handleRefine}
                                        >
                                            {refining ? (
                                                <>
                                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                    Generating...
                                                </>
                                            ) : (
                                                "Refine Resume"
                                            )}
                                        </Button>
                                    </div>
                                    <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg">
                                        <div className="flex gap-2">
                                            <AlertCircle className="h-4 w-4 text-blue-600 shrink-0" />
                                            <p className="text-[11px] text-blue-700 leading-tight">
                                                Instructions will trigger a new AI version targeting the job description and your profile.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </ScrollArea>
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}

function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}
