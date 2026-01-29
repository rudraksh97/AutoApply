// Use Vite env var or default
import React, { useState, useEffect } from 'react';
import { API_URL } from '@/lib/env';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Save, RotateCcw, Sparkles, Target } from 'lucide-react';
import { toast } from 'sonner';

export default function AtsConfigPage() {
    const [prompts, setPrompts] = useState({
        calculate_score: "",
        tailor_resume: ""
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);



    const scoreInputRef = React.useRef<HTMLTextAreaElement>(null);
    const tailorInputRef = React.useRef<HTMLTextAreaElement>(null);

    const insertAtCursor = (inputRef: React.RefObject<HTMLTextAreaElement | null>, textToInsert: string, field: 'calculate_score' | 'tailor_resume') => {
        const textarea = inputRef.current;
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const currentText = prompts[field];

        const newText = currentText.substring(0, start) + textToInsert + currentText.substring(end);

        setPrompts(prev => ({ ...prev, [field]: newText }));

        // Restore cursor position after state update
        setTimeout(() => {
            textarea.focus();
            textarea.setSelectionRange(start + textToInsert.length, start + textToInsert.length);
        }, 0);
    };

    useEffect(() => {
        fetchPrompts();
    }, []);

    const fetchPrompts = async () => {
        try {
            const res = await fetch(`${API_URL}/settings/ats-prompts`);
            if (res.ok) {
                const data = await res.json();
                setPrompts(data);
            } else {
                toast.error("Failed to load ATS configurations");
            }
        } catch {
            toast.error("Failed to fetch prompts");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API_URL}/settings/ats-prompts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(prompts)
            });
            if (res.ok) {
                toast.success("ATS Configuration saved successfully!");
            } else {
                toast.error("Failed to save configuration");
            }
        } catch {
            toast.error("Error connecting to server");
        } finally {
            setSaving(false);
        }
    };

    const handleReset = () => {
        if (confirm("Are you sure you want to reset prompts to defaults?")) {
            fetchPrompts();
            toast.info("Prompts reloaded from current saved state");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12 text-[#296374]">
                <Loader2 className="h-8 w-8 animate-spin" />
            </div>
        );
    }

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            <header className="flex flex-col gap-1">
                <h1 className="text-3xl font-semibold text-[#0C2C55]">ATS Configuration</h1>
                <p className="text-[#296374]">Customize the AI prompts used for ATS scoring and resume tailoring.</p>
            </header>

            <div className="grid gap-6">
                {/* SCORING PROMPT CARD */}
                <Card className="border-[#629FAD]/30 shadow-sm bg-white">
                    <CardHeader className="bg-white border-b border-[#629FAD]/10">
                        <div className="flex items-center gap-2">
                            <Target className="h-5 w-5 text-[#296374]" />
                            <CardTitle className="text-[#0C2C55]">ATS Scoring Prompt</CardTitle>
                        </div>
                        <CardDescription className="text-[#296374]">
                            How the AI evaluates your resume against a job description.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-6">
                        <div className="space-y-4">
                            <div className="flex gap-2">
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(scoreInputRef, "{{job_description}}", 'calculate_score')} className="text-xs h-7 text-[#296374] border-[#629FAD]/30 bg-white hover:bg-[#E8E2DB] rounded-lg">
                                    + Job Description
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(scoreInputRef, "{{resume_text}}", 'calculate_score')} className="text-xs h-7 text-[#296374] border-[#629FAD]/30 bg-white hover:bg-[#E8E2DB] rounded-lg">
                                    + Resume Text
                                </Button>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="score-prompt" className="text-[#0C2C55]">System Prompt</Label>
                                <Textarea
                                    id="score-prompt"
                                    ref={scoreInputRef}
                                    className="min-h-[150px] font-mono text-sm leading-relaxed border-[#629FAD]/30 focus:border-[#0C2C55]"
                                    value={prompts.calculate_score}
                                    onChange={(e) => setPrompts({ ...prompts, calculate_score: e.target.value })}
                                    placeholder="Enter prompt for ATS scoring..."
                                />
                            </div>
                            <div className="bg-[#629FAD]/10 p-4 rounded-lg text-xs text-[#296374] space-y-2 border border-[#629FAD]/20">
                                <p><strong>Input Variables:</strong> <code>{`{{job_description}}`}</code>, <code>{`{{resume_text}}`}</code></p>
                                <p><strong>Required Output (JSON):</strong></p>
                                <pre className="bg-[#0C2C55] text-[#E8E2DB] p-2 rounded border border-[#629FAD]/30 text-[10px] overflow-x-auto">
                                    {`{
  "missing_keywords": ["python", "react"],
  "matched_keywords": ["typescript", "sql"],
  "score": 85,
  "justification": {
    "keyword_match": "Good overlap on core tech but missing some libraries",
    "skill_depth": "Senior level demonstrated"
  }
}`}
                                </pre>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* TAILORING PROMPT CARD */}
                <Card className="border-[#629FAD]/30 shadow-sm bg-white">
                    <CardHeader className="bg-white border-b border-[#629FAD]/10">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-[#296374]" />
                            <CardTitle className="text-[#0C2C55]">Resume Tailoring Prompt</CardTitle>
                        </div>
                        <CardDescription className="text-[#296374]">
                            Instructions for rewriting your LaTeX resume to match specific job requirements.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-6">
                        <div className="space-y-4">
                            <div className="flex gap-2 flex-wrap">
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{job_description}}", 'tailor_resume')} className="text-xs h-7 text-[#296374] border-[#629FAD]/30 bg-white hover:bg-[#E8E2DB]">
                                    + Job Description
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{resume_text}}", 'tailor_resume')} className="text-xs h-7 text-[#296374] border-[#629FAD]/30 bg-white hover:bg-[#E8E2DB]">
                                    + Resume LaTeX
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{missing_keywords}}", 'tailor_resume')} className="text-xs h-7 text-[#296374] border-[#629FAD]/30 bg-white hover:bg-[#E8E2DB]">
                                    + Missing Keywords
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{matched_keywords}}", 'tailor_resume')} className="text-xs h-7 text-[#296374] border-[#629FAD]/30 bg-white hover:bg-[#E8E2DB]">
                                    + Matched Keywords
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{initial_ats_score}}", 'tailor_resume')} className="text-xs h-7 text-[#296374] border-[#629FAD]/30 bg-white hover:bg-[#E8E2DB]">
                                    + Initial Score
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{justification}}", 'tailor_resume')} className="text-xs h-7 text-[#296374] border-[#629FAD]/30 bg-white hover:bg-[#E8E2DB]">
                                    + Justification
                                </Button>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="tailor-prompt" className="text-[#0C2C55]">System Prompt</Label>
                                <Textarea
                                    id="tailor-prompt"
                                    ref={tailorInputRef}
                                    className="min-h-[200px] font-mono text-sm leading-relaxed border-[#629FAD]/30 focus:border-[#0C2C55]"
                                    value={prompts.tailor_resume}
                                    onChange={(e) => setPrompts({ ...prompts, tailor_resume: e.target.value })}
                                    placeholder="Enter prompt for resume tailoring..."
                                />
                            </div>
                            <div className="bg-[#629FAD]/10 p-4 rounded-lg text-xs text-[#296374] space-y-2 border border-[#629FAD]/20">
                                <p><strong>Input Variables:</strong> <code>{`{{job_description}}`}</code>, <code>{`{{resume_text}}`}</code>, etc.</p>
                                <p><strong>Required Output (JSON):</strong></p>
                                <pre className="bg-[#0C2C55] text-[#E8E2DB] p-2 rounded border border-[#629FAD]/30 text-[10px] overflow-x-auto">
                                    {`{
  "final_score": 92,
  "new_latex_code": "\\documentclass{article}...",
  "summary": ["Added 'Next.js' to skills", "Updated project description"]
}`}
                                </pre>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-[#629FAD]/20">
                <Button variant="ghost" onClick={handleReset} className="text-[#296374] hover:text-red-600 hover:bg-red-50">
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Reset Changes
                </Button>
                <Button onClick={handleSave} disabled={saving} className="min-w-[150px] shadow-sm bg-[#0C2C55] text-[#E8E2DB] hover:bg-[#0C2C55]/90 rounded-lg">
                    {saving ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Saving...
                        </>
                    ) : (
                        <>
                            <Save className="mr-2 h-4 w-4" />
                            Save Configuration
                        </>
                    )}
                </Button>
            </div>
        </div>
    );
}
