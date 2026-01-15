"use client"
import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Save, RotateCcw, Sparkles, Target } from 'lucide-react';
import { toast } from 'sonner';

const API_BASE = "http://localhost:8000";

export default function ATSConfigPage() {
    const [prompts, setPrompts] = useState({
        calculate_score: "",
        tailor_resume: ""
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchPrompts();
    }, []);

    const fetchPrompts = async () => {
        try {
            const res = await fetch(`${API_BASE}/settings/ats-prompts`);
            if (res.ok) {
                const data = await res.json();
                setPrompts(data);
            }
        } catch (err) {
            console.error("Failed to fetch prompts", err);
            toast.error("Failed to load ATS configurations");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE}/settings/ats-prompts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(prompts)
            });
            if (res.ok) {
                toast.success("ATS Configuration saved successfully!");
            } else {
                toast.error("Failed to save configuration");
            }
        } catch (err) {
            toast.error("Error connecting to server");
        } finally {
            setSaving(false);
        }
    };

    const handleReset = () => {
        if (confirm("Are you sure you want to reset prompts to defaults?")) {
            // Let backend handle defaults by sending empty or specific request if we had a reset endpoint, 
            // but for now we'll just re-fetch or could define defaults here.
            // Simplest: just fetch again if we haven't modified, or ask user to refresh.
            fetchPrompts();
            toast.info("Prompts reloaded from current saved state");
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
        <div className="container max-w-4xl py-10 space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight mb-2">ATS Configuration</h1>
                <p className="text-muted-foreground">
                    Customize the AI prompts used for ATS scoring and resume tailoring.
                </p>
            </div>

            <div className="grid gap-6">
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
                            <div className="space-y-2">
                                <Label htmlFor="score-prompt">System Prompt</Label>
                                <Textarea
                                    id="score-prompt"
                                    className="min-h-[150px] font-mono text-sm leading-relaxed"
                                    value={prompts.calculate_score}
                                    onChange={(e) => setPrompts({ ...prompts, calculate_score: e.target.value })}
                                    placeholder="Enter prompt for ATS scoring..."
                                />
                            </div>
                            <div className="bg-muted/50 p-3 rounded-md text-xs text-muted-foreground">
                                <strong>Tip:</strong> Ensure you ask the LLM to return JSON with <code className="bg-background px-1 rounded">score</code> and <code className="bg-background px-1 rounded">justification</code> keys.
                            </div>
                        </div>
                    </CardContent>
                </Card>

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
                            <div className="space-y-2">
                                <Label htmlFor="tailor-prompt">System Prompt</Label>
                                <Textarea
                                    id="tailor-prompt"
                                    className="min-h-[200px] font-mono text-sm leading-relaxed"
                                    value={prompts.tailor_resume}
                                    onChange={(e) => setPrompts({ ...prompts, tailor_resume: e.target.value })}
                                    placeholder="Enter prompt for resume tailoring..."
                                />
                            </div>
                            <div className="bg-muted/50 p-3 rounded-md text-xs text-muted-foreground">
                                <strong>Important:</strong> Emphasize that the LLM must preserve the LaTeX structure and return only raw code.
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
