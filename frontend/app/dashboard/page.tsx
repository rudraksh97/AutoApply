"use client"

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card"
import { Play, Square, RefreshCcw } from 'lucide-react';

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
        } catch (e) {
            console.error(e);
            alert("Failed to start automation");
        }
    };

    const stopAutomation = async () => {
        try {
            await axios.post(`${API_URL}/stop`);
            setIsRunning(false); // Optimization, wait for callback ideally
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            </div>

            <div className="grid gap-4 grid-cols-1">
                <Card className="w-full">
                    <CardHeader>
                        <CardTitle>Automation Controls</CardTitle>
                        <CardDescription>Start or stop the background application agent.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex flex-wrap gap-4">
                            <Button
                                variant="default"
                                disabled={isRunning}
                                onClick={() => startAutomation(false)}
                            >
                                <Play className="mr-2 h-4 w-4" /> Run Once
                            </Button>

                            <Button
                                variant="secondary"
                                disabled={isRunning}
                                onClick={() => startAutomation(true)}
                            >
                                <RefreshCcw className="mr-2 h-4 w-4" /> Loop (Every 60s)
                            </Button>

                            <Button
                                variant="destructive"
                                disabled={!isRunning}
                                onClick={stopAutomation}
                            >
                                <Square className="mr-2 h-4 w-4" /> Stop
                            </Button>
                        </div>
                        <div>
                            Status: <span className={isRunning ? "text-green-600 font-bold" : "text-gray-500"}>{isRunning ? "Running" : "Idle"}</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Card className="w-full h-[500px] flex flex-col">
                <CardHeader>
                    <CardTitle>Live Logs</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-hidden">
                    <div className="h-full overflow-y-auto bg-slate-950 text-slate-50 p-4 rounded-md font-mono text-sm space-y-1">
                        {logs.map((log, i) => (
                            <div key={i} className="break-words border-b border-slate-800/50 pb-0.5">{log}</div>
                        ))}
                        <div ref={logsEndRef} />
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
