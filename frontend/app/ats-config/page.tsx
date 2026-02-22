"use client"
import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Save, RotateCcw, Sparkles, Target, Globe } from 'lucide-react';
import { toast } from 'sonner';
import { fetchWithAuth } from '@/lib/api';

export default function ATSConfigPage() {
    const [prompts, setPrompts] = useState({
        calculate_score: "",
        tailor_resume: ""
    });
    const [includeGlobalFeeds, setIncludeGlobalFeeds] = useState(true);
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
        Promise.all([fetchPrompts(), fetchPreferences()]).finally(() => setLoading(false));
    }, []);

    const fetchPrompts = async () => {
        try {
            const res = await fetchWithAuth(`/settings/ats-prompts`);
            if (res.ok) {
                const data = await res.json();
                setPrompts(data);
            } else {
                toast.error("Failed to load ATS configurations");
            }
        } catch (err) {
            console.error("Failed to fetch prompts", err);
        }
    };

    const fetchPreferences = async () => {
        try {
            const res = await fetchWithAuth(`/settings/preferences`);
            if (res.ok) {
                const data = await res.json();
                setIncludeGlobalFeeds(data.include_global_feeds);
            }
        } catch (err) {
            console.error("Failed to fetch preferences", err);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            // Save Prompts
            const pRes = await fetchWithAuth(`/settings/ats-prompts`, {
                method: 'POST',
                body: JSON.stringify(prompts)
            });

            // Save Preferences
            const sRes = await fetchWithAuth(`/settings/preferences`, {
                method: 'PUT',
                body: JSON.stringify({ include_global_feeds: includeGlobalFeeds })
            });

            if (pRes.ok && sRes.ok) {
                toast.success("Settings saved successfully!");
            } else {
                toast.error("Failed to save some settings");
            }
        } catch (err) {
            toast.error("Error connecting to server");
        } finally {
            setSaving(false);
        }
    };

    const handleReset = () => {
        if (confirm("Are you sure you want to reset prompts and settings to saved state?")) {
            fetchPrompts();
            fetchPreferences();
            toast.info("Reloaded from server");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <header className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground">ATS Configuration</h1>
                <p className="text-muted-foreground">
                    Customize AI prompts and general feed settings.
                </p>
            </header>

            <div className="grid gap-6">

                {/* GENERAL SETTINGS CARD */}
                <Card className="border-border shadow-sm">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Globe className="h-5 w-5 text-indigo-500" />
                            <CardTitle>Global Feeds</CardTitle>
                        </div>
                        <CardDescription>
                            Control whether you want to see community-curated job feeds.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center space-x-2">
                            <input
                                type="checkbox"
                                id="globalFeeds"
                                checked={includeGlobalFeeds}
                                onChange={(e) => setIncludeGlobalFeeds(e.target.checked)}
                                className="h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600 cursor-pointer"
                            />
                            <label htmlFor="globalFeeds" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer">
                                Include Global/Admin Feeds in Job Lists
                            </label>
                        </div>
                    </CardContent>
                </Card>

                {/* SCORING PROMPT CARD */}
                <Card className="border-primary/20 shadow-lg hover:shadow-xl transition-shadow duration-300">
                    <CardHeader className="bg-primary/5">
                        <div className="flex items-center gap-2">
                            <Target className="h-5 w-5 text-primary" />
                            <CardTitle>ATS Scoring Prompt</CardTitle>
                        </div>
                        <CardDescription>
                            How the AI evaluates your resume against a job description.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-6">
                        <div className="space-y-4">
                            <div className="flex gap-2">
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(scoreInputRef, "{{job_description}}", 'calculate_score')} className="text-xs h-7">
                                    + Job Description
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(scoreInputRef, "{{resume_text}}", 'calculate_score')} className="text-xs h-7">
                                    + Resume Text
                                </Button>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="score-prompt">System Prompt</Label>
                                <Textarea
                                    id="score-prompt"
                                    ref={scoreInputRef}
                                    className="min-h-[150px] font-mono text-sm leading-relaxed"
                                    value={prompts.calculate_score}
                                    onChange={(e) => setPrompts({ ...prompts, calculate_score: e.target.value })}
                                    placeholder="Enter prompt for ATS scoring..."
                                />
                            </div>
                            <div className="bg-muted/50 p-4 rounded-md text-xs text-muted-foreground space-y-2">
                                <p><strong>Input Variables:</strong> <code>{`{{job_description}}`}</code>, <code>{`{{resume_text}}`}</code></p>
                                <p><strong>Required Output (JSON):</strong></p>
                                <pre className="bg-background p-2 rounded border text-[10px] overflow-x-auto">
                                    {`{
  "missing_keywords": ["python", "react"],
  "matched_keywords": ["typescript", "sql"],
  "score": 85,
  "justification": {
    "keyword_match": "Good overlap on core tech but missing some libraries",
    "skill_depth": "Senior level demonstrated",
    "role_fit": "High",
    "experience_relevance": "Direct competitor experience is a plus",
    "education_fit": "Meets requirements",
    "parsing_quality": "Clean and readable"
  }
}`}
                                </pre>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* TAILORING PROMPT CARD */}
                <Card className="border-secondary/20 shadow-lg hover:shadow-xl transition-shadow duration-300">
                    <CardHeader className="bg-secondary/5">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-secondary" />
                            <CardTitle>Resume Tailoring Prompt</CardTitle>
                        </div>
                        <CardDescription>
                            Instructions for rewriting your LaTeX resume to match specific job requirements.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-6">
                        <div className="space-y-4">
                            <div className="flex gap-2 flex-wrap">
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{job_description}}", 'tailor_resume')} className="text-xs h-7">
                                    + Job Description
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{resume_text}}", 'tailor_resume')} className="text-xs h-7">
                                    + Resume LaTeX
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{missing_keywords}}", 'tailor_resume')} className="text-xs h-7">
                                    + Missing Keywords
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{matched_keywords}}", 'tailor_resume')} className="text-xs h-7">
                                    + Matched Keywords
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{initial_ats_score}}", 'tailor_resume')} className="text-xs h-7">
                                    + Initial Score
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => insertAtCursor(tailorInputRef, "{{justification}}", 'tailor_resume')} className="text-xs h-7">
                                    + Justification
                                </Button>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="tailor-prompt">System Prompt</Label>
                                <Textarea
                                    id="tailor-prompt"
                                    ref={tailorInputRef}
                                    className="min-h-[200px] font-mono text-sm leading-relaxed"
                                    value={prompts.tailor_resume}
                                    onChange={(e) => setPrompts({ ...prompts, tailor_resume: e.target.value })}
                                    placeholder="Enter prompt for resume tailoring..."
                                />
                            </div>
                            <div className="bg-muted/50 p-4 rounded-md text-xs text-muted-foreground space-y-2">
                                <p><strong>Input Variables:</strong> <code>{`{{job_description}}`}</code>, <code>{`{{resume_text}}`}</code>, <code>{`{{missing_keywords}}`}</code>, <code>{`{{matched_keywords}}`}</code>, <code>{`{{initial_ats_score}}`}</code>, <code>{`{{justification}}`}</code></p>
                                <p><strong>Required Output (JSON):</strong></p>
                                <pre className="bg-background p-2 rounded border text-[10px] overflow-x-auto">
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

            <div className="flex items-center justify-between pt-4 border-t">
                <Button variant="ghost" onClick={handleReset} className="text-muted-foreground hover:text-destructive">
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Reset Changes
                </Button>
                <Button onClick={handleSave} disabled={saving} className="min-w-[150px] shadow-md hover:shadow-lg">
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
