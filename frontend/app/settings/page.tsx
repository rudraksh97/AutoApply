"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Key, Puzzle, ExternalLink, CheckCircle2, XCircle, Loader2, Sparkles, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';

interface ModelOption {
    id: string;
    name: string;
    provider: string;
    description: string;
}

export default function SettingsPage() {
    const [openRouterKey, setOpenRouterKey] = useState("");
    const [isConfigured, setIsConfigured] = useState(false);
    const [saving, setSaving] = useState(false);

    // Model selection
    const [availableModels, setAvailableModels] = useState<ModelOption[]>([]);
    const [selectedModel, setSelectedModel] = useState<string>("");
    const [savingModel, setSavingModel] = useState(false);
    const [loadingModels, setLoadingModels] = useState(true);

    // Extension status
    const [extensionStatus, setExtensionStatus] = useState<'checking' | 'installed' | 'not_installed'>('checking');

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

    const fetchModels = async () => {
        setLoadingModels(true);
        try {
            const [modelsRes, selectedRes] = await Promise.all([
                axios.get(`${API_URL}/settings/models`),
                axios.get(`${API_URL}/settings/model`)
            ]);
            setAvailableModels(modelsRes.data);
            setSelectedModel(selectedRes.data.model_id);
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingModels(false);
        }
    };

    const handleModelChange = async (modelId: string) => {
        setSavingModel(true);
        try {
            await axios.post(`${API_URL}/settings/model`, { model_id: modelId });
            setSelectedModel(modelId);
            const model = availableModels.find(m => m.id === modelId);
            toast.success(`Model updated to ${model?.name || modelId}`);
        } catch (e) {
            toast.error("Failed to update model selection");
        } finally {
            setSavingModel(false);
        }
    };

    const checkExtensionStatus = () => {
        setExtensionStatus('checking');

        // Check for the global marker set by content script
        if (typeof window !== 'undefined' && (window as any).__AUTOAPPLY_EXTENSION__) {
            setExtensionStatus('installed');
            return;
        }

        // Send a ping message and wait for response
        const handlePong = (event: MessageEvent) => {
            if (event.data && event.data.type === 'AUTOAPPLY_PONG') {
                setExtensionStatus('installed');
                window.removeEventListener('message', handlePong);
            }
        };

        window.addEventListener('message', handlePong);
        window.postMessage({ type: 'AUTOAPPLY_PING' }, '*');

        // Timeout - if no response after 500ms, extension is not installed
        setTimeout(() => {
            window.removeEventListener('message', handlePong);
            if (extensionStatus === 'checking') {
                // Double check the global marker
                if (typeof window !== 'undefined' && (window as any).__AUTOAPPLY_EXTENSION__) {
                    setExtensionStatus('installed');
                } else {
                    setExtensionStatus('not_installed');
                }
            }
        }, 500);
    };

    useEffect(() => {
        fetchKeyStatus();
        fetchModels();
        checkExtensionStatus();

        // Also listen for the extension ready event
        const handleExtensionReady = () => {
            setExtensionStatus('installed');
        };
        document.addEventListener('autoapply-extension-ready', handleExtensionReady);

        return () => {
            document.removeEventListener('autoapply-extension-ready', handleExtensionReady);
        };
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

            {/* Model Selection */}
            <Card className="shadow-sm border-border/60 overflow-hidden">
                <CardHeader className="border-b bg-muted/30 pb-4">
                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-primary" />
                        Model Selection
                    </CardTitle>
                    <CardDescription>
                        Choose which AI model to use for generating resumes and cover letters.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5 pt-6">
                    {loadingModels ? (
                        <div className="flex items-center gap-3 py-4">
                            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                            <span className="text-sm text-muted-foreground">Loading available models...</span>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div className="grid gap-2">
                                <label htmlFor="model-select" className="text-sm font-medium">
                                    Active Model
                                </label>
                                <div className="relative">
                                    <select
                                        id="model-select"
                                        value={selectedModel}
                                        onChange={(e) => handleModelChange(e.target.value)}
                                        disabled={savingModel}
                                        className="w-full h-10 px-3 pr-10 rounded-md border border-input bg-background text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 appearance-none cursor-pointer"
                                    >
                                        {availableModels.map((model) => (
                                            <option key={model.id} value={model.id}>
                                                {model.name} ({model.provider})
                                            </option>
                                        ))}
                                    </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                                        {savingModel ? (
                                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                        ) : (
                                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Selected model details */}
                            {selectedModel && (
                                <div className="rounded-lg border bg-muted/30 p-4">
                                    {(() => {
                                        const model = availableModels.find(m => m.id === selectedModel);
                                        if (!model) return null;
                                        return (
                                            <div className="space-y-1.5">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-medium text-sm">{model.name}</span>
                                                    <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                                                        {model.provider}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-muted-foreground">{model.description}</p>
                                                <p className="text-[11px] text-muted-foreground/70 font-mono">{model.id}</p>
                                            </div>
                                        );
                                    })()}
                                </div>
                            )}

                            <p className="text-[11px] text-muted-foreground">
                                Models are provided via OpenRouter. Different models have varying capabilities and pricing.
                            </p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Chrome Extension Status */}
            <Card className="shadow-sm border-border/60 overflow-hidden">
                <CardHeader className="border-b bg-muted/30 pb-4">
                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                        <Puzzle className="h-5 w-5 text-primary" />
                        Browser Extension
                    </CardTitle>
                    <CardDescription>
                        Install the AutoApply extension to auto-fill job applications directly in your browser.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5 pt-6">
                    {/* Status Indicator */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {extensionStatus === 'checking' && (
                                <>
                                    <div className="flex items-center justify-center h-10 w-10 rounded-full bg-slate-100">
                                        <Loader2 className="h-5 w-5 text-slate-500 animate-spin" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-sm">Checking extension...</p>
                                        <p className="text-xs text-muted-foreground">Detecting if extension is installed</p>
                                    </div>
                                </>
                            )}
                            {extensionStatus === 'installed' && (
                                <>
                                    <div className="flex items-center justify-center h-10 w-10 rounded-full bg-emerald-100">
                                        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-sm text-emerald-700">Extension Installed</p>
                                        <p className="text-xs text-muted-foreground">AutoApply Helper is active and ready</p>
                                    </div>
                                </>
                            )}
                            {extensionStatus === 'not_installed' && (
                                <>
                                    <div className="flex items-center justify-center h-10 w-10 rounded-full bg-amber-100">
                                        <XCircle className="h-5 w-5 text-amber-600" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-sm text-amber-700">Extension Not Detected</p>
                                        <p className="text-xs text-muted-foreground">Install to enable auto-fill features</p>
                                    </div>
                                </>
                            )}
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={checkExtensionStatus}
                            disabled={extensionStatus === 'checking'}
                        >
                            {extensionStatus === 'checking' ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                'Recheck'
                            )}
                        </Button>
                    </div>

                    {/* Installation Instructions (shown when not installed) */}
                    {extensionStatus === 'not_installed' && (
                        <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 space-y-4">
                            <h4 className="font-semibold text-sm text-amber-900">Installation Instructions</h4>
                            <ol className="text-sm text-amber-800 space-y-2 list-decimal list-inside">
                                <li>Open Chrome and navigate to <code className="bg-amber-100 px-1.5 py-0.5 rounded text-xs">chrome://extensions</code></li>
                                <li>Enable <strong>Developer mode</strong> in the top right corner</li>
                                <li>Click <strong>Load unpacked</strong> and select the <code className="bg-amber-100 px-1.5 py-0.5 rounded text-xs">chrome-extension</code> folder</li>
                                <li>The extension icon should appear in your toolbar</li>
                            </ol>
                            <div className="flex gap-2 pt-2">
                                <Button
                                    variant="default"
                                    size="sm"
                                    className="gap-2"
                                    onClick={() => {
                                        window.open('chrome://extensions', '_blank');
                                        toast.info('Opening Chrome Extensions page...');
                                    }}
                                >
                                    <ExternalLink className="h-4 w-4" />
                                    Open Extensions Page
                                </Button>
                            </div>
                        </div>
                    )}

                    {/* Success state details */}
                    {extensionStatus === 'installed' && (
                        <div className="flex items-center gap-2 p-3 rounded-md bg-emerald-50 border border-emerald-100 text-emerald-800 text-sm">
                            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                            Auto-fill is ready. Open job applications with draft links to populate forms automatically.
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
