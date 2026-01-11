"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Trash2, Plus, RefreshCw, Rss } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from "@/lib/utils";

export default function FeedsPage() {
    const [feeds, setFeeds] = useState<string[]>([]);
    const [newFeed, setNewFeed] = useState("");
    const [loading, setLoading] = useState(true);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchFeeds = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_URL}/feeds`);
            setFeeds(res.data);
        } catch (e) {
            console.error(e);
            toast.error("Failed to fetch feeds");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFeeds();
    }, []);

    const addFeed = async () => {
        if (!newFeed) return;
        try {
            await axios.post(`${API_URL}/feeds`, { url: newFeed });
            setNewFeed("");
            fetchFeeds();
            toast.success("Feed added successfully");
        } catch (e) {
            toast.error("Failed to add feed");
        }
    };

    const removeFeed = async (url: string) => {
        try {
            await axios.delete(`${API_URL}/feeds`, { data: { url } });
            fetchFeeds();
            toast.success("Feed removed");
        } catch (e) {
            toast.error("Failed to remove feed");
        }
    };

    return (
        <div className="space-y-8">
            <header className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground flex items-center gap-2">
                        <Rss className="h-8 w-8 text-primary" />
                        RSS Feeds
                    </h1>
                    <p className="text-muted-foreground">Manage your job sources. New listings will be automatically processed in the background.</p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchFeeds}
                    className="h-10 px-4"
                >
                    <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
                    Refresh
                </Button>
            </header>

            <Card className="shadow-sm border-border/60 overflow-hidden">
                <CardHeader className="border-b bg-muted/30 pb-4">
                    <CardTitle className="text-xl font-semibold">Configure Sources</CardTitle>
                    <CardDescription>Add RSS feed URLs from platforms like Ashby, Greenhouse, or Workable.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6 pt-6">
                    <div className="flex flex-col sm:flex-row gap-3">
                        <Input
                            className="w-full flex-1"
                            placeholder="https://jobs.ashbyhq.com/company/feed or https://boards.greenhouse.io/company/feed"
                            value={newFeed}
                            onChange={(e) => setNewFeed(e.target.value)}
                        />
                        <Button onClick={addFeed} disabled={!newFeed}>
                            <Plus className="h-4 w-4 mr-2" /> Add Feed
                        </Button>
                    </div>

                    <div className="space-y-3">
                        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Active Feeds</h3>
                        <div className="grid gap-3">
                            {feeds.map((feed) => (
                                <div key={feed} className="flex items-center justify-between p-4 border rounded-lg bg-card group hover:shadow-sm transition-shadow">
                                    <div className="flex items-center gap-3 overflow-hidden">
                                        <div className="p-2 rounded bg-primary/10">
                                            <Rss className="h-4 w-4 text-primary" />
                                        </div>
                                        <span className="text-sm font-medium truncate">{feed}</span>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="text-muted-foreground hover:text-red-600 hover:bg-red-50 flex-shrink-0"
                                        onClick={() => removeFeed(feed)}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            ))}
                            {feeds.length === 0 && !loading && (
                                <div className="text-center py-12 border-2 border-dashed rounded-lg bg-muted/20">
                                    <Rss className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
                                    <p className="text-muted-foreground">No RSS feeds configured yet.</p>
                                    <p className="text-sm text-muted-foreground/60 max-w-sm mx-auto mt-2">
                                        Add feeds from Ashby, Greenhouse, or Workable to start discovering jobs automatically.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
