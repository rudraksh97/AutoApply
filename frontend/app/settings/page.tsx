"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
    Cpu,
    Trash2,
    Plus,
    Link as LinkIcon,
    ExternalLink,
    Loader2,
    AlertCircle,
    CheckCircle2,
    XCircle,
    Activity,
    Settings2
} from 'lucide-react';
import { toast } from 'sonner';

interface SDKDefinition {
    id: string;
    provider: string;
    model_name: string;
    display_name: string;
    daily_token_limit: number;
    plans_supported: string[];
}

interface LLMConfig {
    id: string;
    sdk_id: string;
    name: string;
    api_key: string;
    plan_type: string;
    daily_token_limit: number;
    tokens_used_today: number;
    reset_at?: string;
}

interface WorkflowStep {
    id: string;
    name: string;
    description: string;
}

interface WorkflowLink {
    workflow_id: string;
    llm_config_id: string;
}

export default function SettingsPage() {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Data State
    const [sdks, setSdks] = useState<SDKDefinition[]>([]);
    const [inventory, setInventory] = useState<LLMConfig[]>([]);
    const [workflows, setWorkflows] = useState<WorkflowStep[]>([]);
    const [links, setLinks] = useState<WorkflowLink[]>([]);

    // Loading State
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    // Form State (Add Config)
    const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState<string>("");
    const [newConfig, setNewConfig] = useState({
        sdk_id: "",
        name: "",
        api_key: "",
        plan_type: "free",
        daily_token_limit: 0
    });

    // Derived Data
    const uniqueProviders = Array.from(new Set(sdks.map(s => s.provider)));
    const filteredSdks = selectedProvider ? sdks.filter(s => s.provider === selectedProvider) : [];

    // Extension State
    const [extensionStatus, setExtensionStatus] = useState<'checking' | 'installed' | 'not_installed'>('checking');

    // Initial Data Fetch
    const fetchData = async () => {
        try {
            const [sdkRes, invRes, wfRes, linkRes] = await Promise.all([
                axios.get(`${API_URL}/settings/sdks`),
                axios.get(`${API_URL}/settings/llm-inventory`),
                axios.get(`${API_URL}/settings/workflows`),
                axios.get(`${API_URL}/settings/workflow-links`)
            ]);
            setSdks(sdkRes.data);
            setInventory(invRes.data);
            setWorkflows(wfRes.data);
            setLinks(linkRes.data);
        } catch (e) {
            console.error("Failed to load settings data", e);
            toast.error("Failed to load settings. Check backend connection.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        checkExtensionStatus();
    }, []);

    // ------------------------------------------------------------------------
    // LLM Inventory Actions
    // ------------------------------------------------------------------------

    const handleAddConfig = async () => {
        if (!newConfig.sdk_id || !newConfig.name || !newConfig.api_key) {
            toast.error("Please fill all required steps.");
            return;
        }

        setSubmitting(true);
        try {
            await axios.post(`${API_URL}/settings/llm-inventory`, newConfig);
            toast.success("LLM Added Successfully");
            setIsAddDialogOpen(false);
            setNewConfig({ sdk_id: "", name: "", api_key: "", plan_type: "free", daily_token_limit: 0 });
            setSelectedProvider("");
            fetchData();
        } catch (e) {
            toast.error("Failed to add LLM configuration");
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteConfig = async (id: string) => {
        if (!confirm("Are you sure? This will unlink it from any workflows.")) return;
        try {
            await axios.delete(`${API_URL}/settings/llm-inventory/${id}`);
            toast.success("Deleted config");
            fetchData();
        } catch (e) {
            toast.error("Failed to delete config");
        }
    };

    // ------------------------------------------------------------------------
    // Workflow Actions
    // ------------------------------------------------------------------------

    const handleLinkLLM = async (workflow_id: string, llm_config_id: string) => {
        if (!llm_config_id) return;
        try {
            await axios.post(`${API_URL}/settings/workflow-links`, { workflow_id, llm_config_id });
            toast.success("Linked LLM to Workflow");
            fetchData();
        } catch (e) {
            toast.error("Failed to link LLM");
        }
    };

    const handleUnlinkLLM = async (workflow_id: string, llm_config_id: string) => {
        try {
            await axios.delete(`${API_URL}/settings/workflow-links`, {
                data: { workflow_id, llm_config_id }
            });
            toast.success("Unlinked LLM");
            fetchData();
        } catch (e) {
            toast.error("Failed to unlink LLM");
        }
    };

    // ------------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------------

    const getSdk = (id: string) => sdks.find(s => s.id === id);

    const getLinkedConfigs = (workflowId: string) => {
        const linkedIds = links.filter(l => l.workflow_id === workflowId).map(l => l.llm_config_id);
        return inventory.filter(c => linkedIds.includes(c.id));
    };

    const checkExtensionStatus = () => {
        if (typeof window !== 'undefined' && (window as any).__AUTOAPPLY_EXTENSION__) {
            setExtensionStatus('installed');
        } else {
            setExtensionStatus('not_installed');
        }
    };

    if (loading) {
        return <div className="flex h-96 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
    }

    return (
        <div className="space-y-8 pb-20">
            <header className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground">Settings</h1>
                <p className="text-muted-foreground">Manage your LLM Keys and assign them to workflows.</p>
            </header>

            {/* LLM Inventory Section */}
            <section className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                        <Cpu className="h-5 w-5 text-primary" />
                        LLM Inventory
                    </h2>
                    <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
                        <DialogTrigger asChild>
                            <Button size="sm"><Plus className="h-4 w-4 mr-2" /> Add LLM</Button>
                        </DialogTrigger>
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>Add New LLM Configuration</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="grid gap-2">
                                    <Label>Provider</Label>
                                    <select
                                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                        value={selectedProvider}
                                        onChange={(e) => {
                                            setSelectedProvider(e.target.value);
                                            setNewConfig({ ...newConfig, sdk_id: "" });
                                        }}
                                    >
                                        <option value="">Select Provider...</option>
                                        {uniqueProviders.map(p => (
                                            <option key={p} value={p}>{p.toUpperCase()}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="grid gap-2">
                                    <Label>Model</Label>
                                    <select
                                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                        value={newConfig.sdk_id}
                                        disabled={!selectedProvider}
                                        onChange={(e) => {
                                            const sdk = getSdk(e.target.value);
                                            setNewConfig({
                                                ...newConfig,
                                                sdk_id: e.target.value,
                                                daily_token_limit: sdk ? sdk.daily_token_limit : 0
                                            });
                                        }}
                                    >
                                        <option value="">Select a Model...</option>
                                        {filteredSdks.map(sdk => (
                                            <option key={sdk.id} value={sdk.id}>{sdk.model_name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="grid gap-2">
                                    <Label>Friendly Name</Label>
                                    <Input
                                        placeholder="e.g. My Personal Gemini Key"
                                        value={newConfig.name}
                                        onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label>API Key</Label>
                                    <Input
                                        type="password"
                                        placeholder="sk-..."
                                        value={newConfig.api_key}
                                        onChange={(e) => setNewConfig({ ...newConfig, api_key: e.target.value })}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label>Plan Type</Label>
                                    <select
                                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                        value={newConfig.plan_type}
                                        onChange={(e) => setNewConfig({ ...newConfig, plan_type: e.target.value })}
                                    >
                                        <option value="free">Free Tier</option>
                                        <option value="paid">Paid Tier</option>
                                    </select>
                                </div>
                            </div>
                            <DialogFooter>
                                <Button onClick={handleAddConfig} disabled={submitting}>
                                    {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                    Save Configuration
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {inventory.map(config => {
                        const sdk = getSdk(config.sdk_id);
                        const usagePercent = Math.min(100, (config.tokens_used_today / config.daily_token_limit) * 100);

                        return (
                            <Card key={config.id} className="relative overflow-hidden">
                                <CardHeader className="pb-2">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <CardTitle className="text-base font-medium">{config.name}</CardTitle>
                                            <CardDescription className="text-xs mt-1">{sdk?.display_name}</CardDescription>
                                        </div>
                                        <Badge variant={config.plan_type === 'paid' ? 'default' : 'secondary'} className="uppercase text-[10px]">
                                            {config.plan_type}
                                        </Badge>
                                    </div>
                                </CardHeader>
                                <CardContent className="pb-2">
                                    <div className="space-y-3">
                                        <div className="space-y-1">
                                            <div className="flex justify-between text-xs text-muted-foreground">
                                                <span>Daily Usage</span>
                                                <span>{config.tokens_used_today.toLocaleString()} / {config.daily_token_limit.toLocaleString()}</span>
                                            </div>
                                            <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-primary transition-all duration-500"
                                                    style={{ width: `${usagePercent}%` }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                                <CardFooter className="pt-2 flex justify-end">
                                    <Button variant="ghost" size="sm" onClick={() => handleDeleteConfig(config.id)} className="text-destructive h-8 px-2">
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </CardFooter>
                            </Card>
                        );
                    })}
                    {inventory.length === 0 && (
                        <div className="col-span-full p-8 border border-dashed rounded-lg text-center text-muted-foreground">
                            No LLMs configured. Add one to get started.
                        </div>
                    )}
                </div>
            </section>

            {/* Workflow Configuration Section */}
            <section className="space-y-4 pt-4 border-t">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Workflow Configuration
                </h2>
                <p className="text-sm text-muted-foreground">Assign LLMs to specific automation steps. Multiple LLMs will load-balance based on available tokens.</p>

                <div className="grid gap-6">
                    {workflows.map(wf => {
                        const linkedConfigs = getLinkedConfigs(wf.id);

                        return (
                            <Card key={wf.id}>
                                <CardHeader className="pb-3 bg-muted/20">
                                    <CardTitle className="text-base">{wf.name}</CardTitle>
                                    <CardDescription>{wf.description}</CardDescription>
                                </CardHeader>
                                <CardContent className="pt-4 space-y-4">
                                    <div className="space-y-2">
                                        <Label className="text-xs uppercase text-muted-foreground font-bold tracking-wider">Assigned LLM Pools</Label>
                                        <div className="flex flex-wrap gap-2">
                                            {linkedConfigs.map(c => (
                                                <Badge key={c.id} variant="outline" className="pl-2 pr-1 py-1 flex gap-2 items-center bg-background">
                                                    <span className="truncate max-w-[150px]">{c.name}</span>
                                                    <div className="h-3 w-[1px] bg-border" />
                                                    <span className="text-[10px] text-muted-foreground">
                                                        {(c.daily_token_limit - c.tokens_used_today).toLocaleString()} left
                                                    </span>
                                                    <button onClick={() => handleUnlinkLLM(wf.id, c.id)} className="ml-1 hover:bg-destructive/10 rounded-full p-0.5 text-muted-foreground hover:text-destructive transition-colors">
                                                        <XCircle className="h-3 w-3" />
                                                    </button>
                                                </Badge>
                                            ))}
                                            {linkedConfigs.length === 0 && (
                                                <span className="text-sm text-destructive flex items-center gap-1">
                                                    <AlertCircle className="h-3 w-3" /> No LLM assigned! This step will fail.
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2 max-w-sm">
                                        <select
                                            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors"
                                            onChange={(e) => {
                                                if (e.target.value) {
                                                    handleLinkLLM(wf.id, e.target.value);
                                                    e.target.value = ""; // Reset
                                                }
                                            }}
                                        >
                                            <option value="">+ Link another LLM...</option>
                                            {inventory
                                                .filter(inv => !linkedConfigs.find(l => l.id === inv.id))
                                                .map(inv => (
                                                    <option key={inv.id} value={inv.id}>{inv.name} ({getSdk(inv.sdk_id)?.display_name})</option>
                                                ))
                                            }
                                        </select>
                                    </div>
                                </CardContent>
                            </Card>
                        )
                    })}
                </div>
            </section>

            {/* Chrome Extension Status */}
            <Card className="shadow-sm border-border/60 overflow-hidden mt-8">
                <CardHeader className="border-b bg-muted/30 pb-4">
                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                        <ExternalLink className="h-5 w-5 text-primary" />
                        Browser Extension
                    </CardTitle>
                    <CardDescription>
                        Status of the AutoApply helper extension.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5 pt-6">
                    <div className="flex items-center gap-3">
                        {extensionStatus === 'installed' ? (
                            <div className="flex items-center gap-2 text-emerald-600 font-medium">
                                <CheckCircle2 className="h-5 w-5" /> Extension Installed & Active
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 text-amber-600 font-medium">
                                <AlertCircle className="h-5 w-5" /> Extension Not Detected
                            </div>
                        )}
                        <Button variant="outline" size="sm" onClick={checkExtensionStatus}>Recheck</Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
