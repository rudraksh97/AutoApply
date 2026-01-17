"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Key, Puzzle, ExternalLink, CheckCircle2, XCircle, Loader2, Sparkles, ChevronDown, Check, ShieldCheck, Zap, Info, Save, KeyRound } from 'lucide-react';
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
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

    // NEW: Plan and Multi-SDK
    const [planType, setPlanType] = useState<"paid" | "free">("paid");
    const [freeConfigs, setFreeConfigs] = useState<any[]>([]);
    const [llmOptions, setLlmOptions] = useState<{ sdks: any[] }>({ sdks: [] });
    const [newConfig, setNewConfig] = useState({ sdk: "", model: "", api_key: "" });
    const [addingConfig, setAddingConfig] = useState(false);

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

    const fetchPlanAndConfigs = async () => {
        try {
            const [planRes, configsRes, optionsRes] = await Promise.all([
                axios.get(`${API_URL}/settings/plan`),
                axios.get(`${API_URL}/settings/free-configs`),
                axios.get(`${API_URL}/settings/llm-options`)
            ]);
            setPlanType(planRes.data.plan_type);
            setFreeConfigs(configsRes.data);
            setLlmOptions(optionsRes.data);

            // Set default SDK/Model for new config if options available
            if (optionsRes.data.sdks.length > 0) {
                const firstSdk = optionsRes.data.sdks[0];
                setNewConfig(prev => ({
                    ...prev,
                    sdk: firstSdk.id,
                    model: firstSdk.models[0]
                }));
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handlePlanChange = async (type: "paid" | "free") => {
        try {
            await axios.post(`${API_URL}/settings/plan`, { plan_type: type });
            setPlanType(type);
            toast.success(`Plan switched to ${type}`);
        } catch (e) {
            toast.error("Failed to change plan");
        }
    };

    const addFreeConfig = async () => {
        if (!newConfig.api_key || !newConfig.sdk || !newConfig.model) {
            toast.error("Please fill all fields");
            return;
        }
        setAddingConfig(true);
        try {
            await axios.post(`${API_URL}/settings/free-configs`, newConfig);
            toast.success("Configuration added");
            setNewConfig(prev => ({ ...prev, api_key: "" }));
            fetchPlanAndConfigs();
        } catch (e) {
            toast.error("Failed to add configuration");
        } finally {
            setAddingConfig(false);
        }
    };

    const removeFreeConfig = async (index: number) => {
        try {
            await axios.delete(`${API_URL}/settings/free-configs/${index}`);
            toast.success("Configuration removed");
            fetchPlanAndConfigs();
        } catch (e) {
            toast.error("Failed to remove configuration");
        }
    };

    useEffect(() => {
        fetchKeyStatus();
        fetchModels();
        checkExtensionStatus();
        fetchPlanAndConfigs();

        // Also listen for the extension ready event
        const handleExtensionReady = () => {
            setExtensionStatus('installed');
        };
        document.addEventListener('autoapply-extension-ready', handleExtensionReady);

        return () => {
            document.removeEventListener('autoapply-extension-ready', handleExtensionReady);
        };
    }, []);

    return (
        <div className="space-y-8">
            <header className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground">Settings</h1>
                <p className="text-muted-foreground">Configure your application keys and preferences.</p>
            </header>

            <div className="flex bg-muted p-1 rounded-lg border mb-8 max-w-md">
                <Button
                    variant={planType === 'paid' ? 'default' : 'ghost'}
                    className="flex-1 rounded"
                    onClick={() => handlePlanChange('paid')}
                >
                    Paid Plan (OpenRouter)
                </Button>
                <Button
                    variant={planType === 'free' ? 'default' : 'ghost'}
                    className="flex-1 rounded"
                    onClick={() => handlePlanChange('free')}
                >
                    Free Plan (Multi-SDK)
                </Button>
            </div>

            {planType === 'paid' ? (
                <>
                    <Card className="shadow-sm border-border/60 overflow-hidden">
                        <CardHeader className="border-b bg-muted/30 pb-4">
                            <div className="flex items-center justify-between">
                                <div className="space-y-1">
                                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                                        <ShieldCheck className="h-5 w-5 text-primary" />
                                        API Configuration
                                    </CardTitle>
                                    <CardDescription>Configure your provider's access</CardDescription>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-6 pt-6">
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <label htmlFor="openrouter-key" className="text-sm font-medium">OpenRouter API Key</label>
                                    <div className="flex gap-2">
                                        <div className="relative flex-1">
                                            <Input
                                                id="openrouter-key"
                                                type="password"
                                                placeholder="sk-or-..."
                                                value={openRouterKey}
                                                onChange={(e) => setOpenRouterKey(e.target.value)}
                                                className="pr-10"
                                            />
                                            <KeyRound className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                        </div>
                                        <Button onClick={saveKey} disabled={saving}>
                                            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
                                            Save
                                        </Button>
                                    </div>
                                    {isConfigured && (
                                        <p className="text-xs text-emerald-600 flex items-center gap-1">
                                            <ShieldCheck className="h-3 w-3" /> API Key is securely stored
                                        </p>
                                    )}
                                </div>

                                <div className="p-4 rounded-lg border bg-blue-50/50 border-blue-100 flex gap-3">
                                    <Info className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                                    <div className="space-y-1">
                                        <p className="text-sm font-medium text-blue-900">Why OpenRouter?</p>
                                        <p className="text-xs text-blue-700 leading-relaxed">
                                            OpenRouter gives you access to multiple LLM providers (Anthropic, OpenAI, Meta) with a single API key.
                                            Ensure your key has credits to enable AI-powered features.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="shadow-sm border-border/60 overflow-hidden">
                        <CardHeader className="border-b bg-muted/30 pb-4">
                            <CardTitle className="text-xl font-semibold flex items-center gap-2">
                                <Zap className="h-5 w-5 text-primary" />
                                Model Selection
                            </CardTitle>
                            <CardDescription>Select the brain for your application automation</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6 pt-6">
                            {loadingModels ? (
                                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                                    <p className="text-sm text-muted-foreground">Loading available models...</p>
                                </div>
                            ) : (
                                <div className="grid gap-3">
                                    {availableModels.map((model) => {
                                        const isSelected = selectedModel === model.id;
                                        return (
                                            <div
                                                key={model.id}
                                                onClick={() => handleModelChange(model.id)}
                                                className={cn(
                                                    "group relative flex flex-col p-4 rounded-xl border-2 transition-all cursor-pointer",
                                                    isSelected
                                                        ? "border-primary bg-primary/5 shadow-sm"
                                                        : "border-border/50 hover:border-border hover:bg-muted/30"
                                                )}
                                            >
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-semibold">{model.name}</span>
                                                        <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider px-1.5 h-4">
                                                            {model.provider}
                                                        </Badge>
                                                        {isSelected && (
                                                            <div className="flex items-center gap-1 text-[10px] text-primary font-bold bg-primary/10 px-1.5 py-0.5 rounded uppercase tracking-wider">
                                                                Active
                                                            </div>
                                                        )}
                                                    </div>
                                                    {isSelected && <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center"><Check className="h-3 w-3 text-white" /></div>}
                                                </div>
                                                <p className="text-sm text-muted-foreground mr-8">{model.description}</p>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            <p className="text-[11px] text-muted-foreground">
                                Models are provided via OpenRouter. Different models have varying capabilities and pricing.
                            </p>
                        </CardContent>
                    </Card>
                </>
            ) : (
                <Card className="shadow-sm border-border/60 overflow-hidden">
                    <CardHeader className="border-b bg-muted/30 pb-4">
                        <CardTitle className="text-xl font-semibold flex items-center gap-2">
                            <Puzzle className="h-5 w-5 text-primary" />
                            Free Plan Model Configurations
                        </CardTitle>
                        <CardDescription>
                            Add multiple API keys and models to bypass rate limits. They will be used in a round-robin fashion.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6 pt-6">
                        {/* New Config Form */}
                        <div className="grid gap-4 p-4 rounded-lg border bg-muted/10">
                            <h3 className="font-medium text-sm">Add New Configuration</h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-medium">SDK Name</label>
                                    <select
                                        className="w-full h-10 px-3 rounded-md border text-sm"
                                        value={newConfig.sdk}
                                        onChange={(e) => {
                                            const sdk = llmOptions.sdks.find(s => s.id === e.target.value);
                                            setNewConfig({
                                                ...newConfig,
                                                sdk: e.target.value,
                                                model: sdk?.models[0] || ""
                                            });
                                        }}
                                    >
                                        <option value="" disabled>Select SDK</option>
                                        {llmOptions.sdks.map(sdk => (
                                            <option key={sdk.id} value={sdk.id}>{sdk.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-medium">Model</label>
                                    <select
                                        className="w-full h-10 px-3 rounded-md border text-sm"
                                        value={newConfig.model}
                                        onChange={(e) => setNewConfig({ ...newConfig, model: e.target.value })}
                                    >
                                        <option value="" disabled>Select Model</option>
                                        {llmOptions.sdks.find(s => s.id === newConfig.sdk)?.models.map((m: any) => (
                                            <option key={m.id} value={m.id}>{m.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-medium">API Key</label>
                                    <Input
                                        type="password"
                                        placeholder="sk-..."
                                        value={newConfig.api_key}
                                        onChange={(e) => setNewConfig({ ...newConfig, api_key: e.target.value })}
                                    />
                                </div>
                            </div>
                            <Button onClick={addFreeConfig} disabled={addingConfig}>
                                {addingConfig ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                Add Configuration
                            </Button>
                        </div>

                        {/* Config List */}
                        <div className="space-y-3">
                            <h3 className="font-medium text-sm">Active Configurations ({freeConfigs.length})</h3>
                            {freeConfigs.length === 0 ? (
                                <p className="text-sm text-muted-foreground py-4 text-center border rounded-lg border-dashed">
                                    No configurations added yet.
                                </p>
                            ) : (
                                <div className="grid gap-3">
                                    {freeConfigs.map((config, index) => (
                                        <div key={index} className="flex items-center justify-between p-3 rounded-md border bg-card">
                                            <div className="flex flex-col">
                                                <span className="font-medium text-sm">{config.sdk.toUpperCase()} / {config.model}</span>
                                                <span className="text-xs text-muted-foreground font-mono">{config.api_key}</span>
                                            </div>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => removeFreeConfig(index)}
                                                className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                            >
                                                <XCircle className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

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
