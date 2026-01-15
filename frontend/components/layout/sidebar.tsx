"use client"
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Briefcase, User, Settings, Rss, Cpu } from 'lucide-react';

export function Sidebar({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    const pathname = usePathname();
    const items = [
        { href: "/feeds", title: "RSS Feeds", icon: Rss },
        { href: "/jobs", title: "Job History", icon: Briefcase },
        { href: "/profile", title: "My Profile", icon: User },
        { href: "/ats-config", title: "ATS Configuration", icon: Cpu },
        { href: "/settings", title: "Settings", icon: Settings },
    ];

    return (
        <div className={cn("pb-12 min-h-screen border-r border-border bg-sidebar text-sidebar-foreground w-64 hidden md:block", className)} {...props}>
            <div className="space-y-4 py-4">
                <div className="px-3 py-2">
                    <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
                        AutoApply 🚀
                    </h2>
                    <div className="space-y-1">
                        {items.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-sidebar-hover hover:text-foreground transition-colors",
                                    pathname === item.href ? "bg-sidebar-hover text-foreground font-semibold" : "text-muted-foreground"
                                )}
                            >
                                <item.icon className="mr-2 h-4 w-4" />
                                {item.title}
                            </Link>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
