"use client";

import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/api";
import { Feed } from "@/types/feed";
import { useAuth } from "@/components/providers/auth-provider";
import { toast } from "sonner";
import { Trash2, Plus, Globe, Lock } from "lucide-react";

export default function FeedsPage() {
    const { user } = useAuth();
    const [feeds, setFeeds] = useState<Feed[]>([]);
    const [loading, setLoading] = useState(true);
    const [newUrl, setNewUrl] = useState("");
    const [newName, setNewName] = useState("");
    const [isGlobal, setIsGlobal] = useState(false);
    const [adding, setAdding] = useState(false);

    const isAdmin = user?.roles.includes("admin");

    useEffect(() => {
        loadFeeds();
    }, []);

    const loadFeeds = async () => {
        try {
            const res = await fetchWithAuth("/feeds");
            if (res.ok) {
                setFeeds(await res.json());
            } else {
                toast.error("Failed to load feeds");
            }
        } catch (err) {
            toast.error("Error loading feeds");
        } finally {
            setLoading(false);
        }
    };

    const handleAddFeed = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newUrl) return;
        setAdding(true);

        try {
            const res = await fetchWithAuth("/feeds", {
                method: "POST",
                body: JSON.stringify({
                    url: newUrl,
                    name: newName || newUrl,
                    is_global: isAdmin ? isGlobal : false,
                }),
            });

            if (res.ok) {
                const newFeed = await res.json();
                setFeeds([...feeds, newFeed]);
                setNewUrl("");
                setNewName("");
                setIsGlobal(false);
                toast.success("Feed added");
            } else {
                const err = await res.json();
                toast.error(err.detail || "Failed to add feed");
            }
        } catch (err) {
            toast.error("Error adding feed");
        } finally {
            setAdding(false);
        }
    };

    const handleDelete = async (feedId: string) => {
        if (!confirm("Are you sure you want to delete this feed?")) return;

        try {
            const res = await fetchWithAuth(`/feeds/${feedId}`, {
                method: "DELETE",
            });

            if (res.ok) {
                setFeeds(feeds.filter((f) => f.id !== feedId));
                toast.success("Feed removed");
            } else {
                const err = await res.json();
                toast.error(err.detail || "Failed to remove feed");
            }
        } catch (err) {
            toast.error("Error removing feed");
        }
    };

    if (loading) return <div className="p-4">Loading feeds...</div>;

    return (
        <div className="max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">RSS Feeds</h1>

            {/* Add Feed Form */}
            <div className="bg-card p-6 rounded-lg border shadow-sm mb-8">
                <h2 className="text-lg font-semibold mb-4">Add New Feed</h2>
                <form onSubmit={handleAddFeed} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">Feed URL</label>
                            <input
                                type="url"
                                required
                                value={newUrl}
                                onChange={(e) => setNewUrl(e.target.value)}
                                placeholder="https://example.com/rss"
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">Name (Optional)</label>
                            <input
                                type="text"
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                placeholder="My Tech Feed"
                                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            />
                        </div>
                    </div>

                    {isAdmin && (
                        <div className="flex items-center space-x-2">
                            <input
                                type="checkbox"
                                id="isGlobal"
                                checked={isGlobal}
                                onChange={(e) => setIsGlobal(e.target.checked)}
                                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600"
                            />
                            <label htmlFor="isGlobal" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                Global Feed (Visible to all users)
                            </label>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={adding}
                        className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
                    >
                        {adding ? "Adding..." : <><Plus className="mr-2 h-4 w-4" /> Add Feed</>}
                    </button>
                </form>
            </div>

            {/* Feeds List */}
            <div className="grid gap-4">
                {feeds.map((feed) => (
                    <div key={feed.id} className="bg-card p-4 rounded-lg border shadow-sm flex items-center justify-between">
                        <div className="min-w-0 flex-1 mr-4">
                            <div className="flex items-center gap-2 mb-1">
                                <h3 className="font-semibold truncate">{feed.name}</h3>
                                {feed.is_global ? (
                                    <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 text-foreground">
                                        <Globe className="h-3 w-3 mr-1" /> Global
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 text-muted-foreground">
                                        <Lock className="h-3 w-3 mr-1" /> Private
                                    </span>
                                )}
                            </div>
                            <p className="text-sm text-muted-foreground truncate">{feed.url}</p>
                        </div>

                        {(feed.user_id === user?.id || isAdmin) && (
                            <button
                                onClick={() => handleDelete(feed.id!)}
                                className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                                title="Remove Feed"
                            >
                                <Trash2 className="h-4 w-4" />
                            </button>
                        )}
                    </div>
                ))}
                {feeds.length === 0 && (
                    <div className="text-center p-8 text-muted-foreground">
                        No feeds found. Add one above!
                    </div>
                )}
            </div>
        </div>
    );
}
