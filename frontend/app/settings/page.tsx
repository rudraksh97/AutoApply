"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Trash2, Upload, Plus } from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
    const [feeds, setFeeds] = useState<string[]>([]);
    const [newFeed, setNewFeed] = useState("");
    const [uploading, setUploading] = useState(false);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchFeeds = async () => {
        try {
            const res = await axios.get(`${API_URL}/feeds`);
            setFeeds(res.data);
        } catch (e) {
            console.error(e);
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
        } catch (e) {
            toast.error("Failed to add feed");
        }
    };

    const removeFeed = async (url: string) => {
        try {
            await axios.delete(`${API_URL}/feeds`, { data: { url } });
            fetchFeeds();
        } catch (e) {
            toast.error("Failed to remove feed");
        }
    };



    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

            <Card className="w-full">
                <CardHeader>
                    <CardTitle>RSS Feeds</CardTitle>
                    <CardDescription>Manage job sources.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex flex-col sm:flex-row gap-2">
                        <Input
                            className="w-full flex-1"
                            placeholder="https://example.com/feed.xml"
                            value={newFeed}
                            onChange={(e) => setNewFeed(e.target.value)}
                        />
                        <Button onClick={addFeed}><Plus className="h-4 w-4 mr-2" /> Add</Button>
                    </div>
                    <div className="space-y-2">
                        {feeds.map((feed) => (
                            <div key={feed} className="flex items-center justify-between p-2 border rounded bg-slate-50">
                                <span className="text-sm truncate">{feed}</span>
                                <Button variant="ghost" size="icon" onClick={() => removeFeed(feed)}>
                                    <Trash2 className="h-4 w-4 text-red-500" />
                                </Button>
                            </div>
                        ))}
                        {feeds.length === 0 && <div className="text-sm text-gray-500">No feeds configured.</div>}
                    </div>
                </CardContent>
            </Card>


        </div>
    )
}
