"use client"

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card"
import { Play, Square, RefreshCcw } from 'lucide-react';
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export default function DashboardPage() {
    const [isRunning, setIsRunning] = useState(false);
    const [logs, setLogs] = useState<string[]>([]);
    const logsEndRef = useRef<HTMLDivElement>(null);
    const [ws, setWs] = useState<WebSocket | null>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Auto-scroll logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    // Check running status on mount
    useEffect(() => {
        const checkStatus = async () => {
            try {
                const res = await axios.get(`${API_URL}/status`);
                setIsRunning(res.data.running);
            } catch (e) {
                console.error("Failed to fetch status", e);
            }
        };
        checkStatus();
    }, [API_URL]);

    // Connect WebSocket
    useEffect(() => {
        // In Docker, browser connects to localhost:8000 exposed port
        // But if we are running in dev mode locally, it's also localhost:8000
        // We handle the URL carefully.
        const wsUrl = API_URL.replace("http", "ws") + "/ws/logs";
        console.log("Connecting WS to", wsUrl);
        const socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log("WebSocket Connected");
            // system message
            setLogs(prev => [...prev, ">>> Connected to Log Stream"]);
        };

        socket.onmessage = (event) => {
            setLogs(prev => [...prev.slice(-99), event.data]); // Keep last 100
        };

        socket.onclose = () => {
            console.log("WebSocket Disconnected");
        };

        setWs(socket);

        return () => {
            socket.close();
        };
    }, [API_URL]);

    const startAutomation = async (continuous: boolean) => {
        try {
            await axios.post(`${API_URL}/start`, null, { params: { continuous } });
            setIsRunning(true);
            toast.success("Automation started successfully");
        } catch (e: any) {
            console.error(e);
            toast.error("Failed to start automation: " + (e.response?.data?.detail || e.message));
        }
    };

    const stopAutomation = async () => {
        try {
            await axios.post(`${API_URL}/stop`);
            setIsRunning(false); // Optimization, wait for callback ideally
            toast.success("Automation stopped");
        } catch (e: any) {
            console.error(e);
            toast.error("Failed to stop automation");
        }
    };

    return (
        <div className="space-y-8">
            <header className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground">Dashboard</h1>
                <p className="text-muted-foreground">Monitor and control your automated job search agent.</p>
            </header>

            <div className="grid gap-6">
                <Card className="shadow-sm border-border/60">
                    <CardHeader className="pb-4">
                        <CardTitle className="text-xl font-semibold">Automation Controls</CardTitle>
                        <CardDescription>Start or stop the background application agent.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex flex-wrap gap-3">
                            <Button
                                variant="default"
                                size="lg"
                                disabled={isRunning}
                                onClick={() => startAutomation(false)}
                                className="px-6"
                            >
                                <Play className="mr-2 h-4 w-4" /> Run Once
                            </Button>

                            <Button
                                variant="outline"
                                size="lg"
                                disabled={isRunning}
                                onClick={() => startAutomation(true)}
                                className="px-6"
                            >
                                <RefreshCcw className="mr-2 h-4 w-4" /> Loop (Every 60s)
                            </Button>

                            <div className="flex-1" />

                            <Button
                                variant="destructive"
                                size="lg"
                                disabled={!isRunning}
                                onClick={stopAutomation}
                                className="px-6"
                            >
                                <Square className="mr-2 h-4 w-4" /> Stop
                            </Button>
                        </div>

                        <div className="flex items-center gap-2 pt-2 border-t border-border/40">
                            <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Status:</span>
                            <div className="flex items-center gap-2">
                                <div className={cn("h-2 w-2 rounded-full", isRunning ? "bg-green-500 animate-pulse" : "bg-gray-300")} />
                                <span className={cn("text-sm font-bold", isRunning ? "text-green-600" : "text-gray-500 uppercase")}>
                                    {isRunning ? "Running" : "Idle"}
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="shadow-sm border-border/60 flex flex-col h-[600px]">
                    <CardHeader className="pb-4">
                        <CardTitle className="text-xl font-semibold">Live Logs</CardTitle>
                        <CardDescription>Real-time execution details from the assistant.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-hidden pt-0">
                        <div className="h-full overflow-y-auto bg-[#1a1a1a] text-[#e0e0e0] p-6 rounded-lg font-mono text-xs leading-relaxed border border-border/10 selection:bg-accent/20">
                            {logs.length === 0 ? (
                                <div className="text-muted-foreground/40 italic">Waiting for logs...</div>
                            ) : (
                                logs.map((log, i) => (
                                    <div key={i} className="py-0.5 border-b border-white/[0.03] last:border-0 opacity-90 hover:opacity-100 transition-opacity">
                                        <span className="text-accent/60 mr-2 opacity-50 select-none">[{i + 1}]</span>
                                        {log}
                                    </div>
                                ))
                            )}
                            <div ref={logsEndRef} />
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
