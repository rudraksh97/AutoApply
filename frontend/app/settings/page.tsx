"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Key } from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
    const [openRouterKey, setOpenRouterKey] = useState("");
    const [isConfigured, setIsConfigured] = useState(false);
    const [saving, setSaving] = useState(false);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchKeyStatus = async () => {
        try {
            const res = await axios.get(`${API_URL}/settings/keys`);
            const orKey = res.data.find((k: any) => k.name === "OPENROUTER_API_KEY");
            if (orKey) {
                setIsConfigured(orKey.configured);
            }
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        fetchKeyStatus();
    }, []);

    const saveKey = async () => {
        if (!openRouterKey) return;
        setSaving(true);
        try {
            await axios.post(`${API_URL}/settings/keys`, {
                key_name: "OPENROUTER_API_KEY",
                key_value: openRouterKey
            });
            setOpenRouterKey("");
            fetchKeyStatus();
            toast.success("OpenRouter API key updated successfully");
        } catch (e) {
            toast.error("Failed to update API key");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-8">
            <header className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground">Settings</h1>
                <p className="text-muted-foreground">Configure your application keys and preferences.</p>
            </header>

            <Card className="shadow-sm border-border/60 overflow-hidden">
                <CardHeader className="border-b bg-muted/30 pb-4">
                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                        <Key className="h-5 w-5 text-primary" />
                        API Configuration
                    </CardTitle>
                    <CardDescription>
                        Set your API keys to enable LLM-driven features and browser automation.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6 pt-6">
                    <div className="space-y-4">
                        <div className="grid gap-2">
                            <label htmlFor="openrouter-key" className="text-sm font-medium">
                                OpenRouter API Key
                            </label>
                            <div className="flex gap-3">
                                <Input
                                    id="openrouter-key"
                                    type="password"
                                    placeholder={isConfigured ? "Key is configured (enter new one to update)" : "sk-or-v1-..."}
                                    value={openRouterKey}
                                    onChange={(e) => setOpenRouterKey(e.target.value)}
                                    className="flex-1"
                                />
                                <Button onClick={saveKey} disabled={saving || !openRouterKey}>
                                    {saving ? "Saving..." : "Save Key"}
                                </Button>
                            </div>
                            <p className="text-[11px] text-muted-foreground">
                                Your key is stored securely in the local environment file.
                            </p>
                        </div>

                        {isConfigured && (
                            <div className="flex items-center gap-2 p-3 rounded-md bg-emerald-50 border border-emerald-100 text-emerald-800 text-sm">
                                <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                                OpenRouter integration is active.
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
