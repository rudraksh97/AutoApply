"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { fetchWithAuth } from "@/lib/api";
import { Feed } from "@/types/feed";
import { useAuth } from "./auth-provider";

interface FeedContextType {
    feeds: Feed[];
    selectedFeedId: string | null;
    setSelectedFeedId: (id: string | null) => void;
    loading: boolean;
    refreshFeeds: () => Promise<void>;
}

const FeedContext = createContext<FeedContextType | undefined>(undefined);

export function FeedProvider({ children }: { children: ReactNode }) {
    const [feeds, setFeeds] = useState<Feed[]>([]);
    const [selectedFeedId, setSelectedFeedId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const { user } = useAuth();

    const loadFeeds = async () => {
        if (!user) {
            setFeeds([]);
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            const res = await fetchWithAuth("/feeds?mode=system");
            if (res.ok) {
                const data = await res.json();
                setFeeds(data);
            }
        } catch (err) {
            console.error("Error loading feeds", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadFeeds();
    }, [user]);

    return (
        <FeedContext.Provider value={{
            feeds,
            selectedFeedId,
            setSelectedFeedId,
            loading,
            refreshFeeds: loadFeeds
        }}>
            {children}
        </FeedContext.Provider>
    );
}

export const useFeeds = () => {
    const context = useContext(FeedContext);
    if (context === undefined) {
        throw new Error("useFeeds must be used within a FeedProvider");
    }
    return context;
}
