"use client"
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Briefcase, User, Settings, Rss, Cpu, Users, LogOut, LayoutDashboard } from 'lucide-react';
import { useAuth } from '@/components/providers/auth-provider';

export function Sidebar({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    // Do not show sidebar on login or register pages
    const isAuthPage = pathname === '/login' || pathname === '/register';
    if (isAuthPage) return null;

    // Define Role-Based Access
    // Admin: All
    // Basic: Feeds, History, Profile, Settings
    // Customer: Jobs (Simple), Profile

    const isAdmin = user?.roles?.includes('admin') ?? false;
    const isBasic = user?.roles?.includes('basic') || isAdmin;
    // A pure customer sees only Jobs — no Profile, no Settings, no Feeds.
    const isCustomerOnly = !isBasic && (user?.roles?.includes('customer') ?? false);

    const items = [
        // Full-access users
        { href: "/profile", title: "My Profile", icon: User, show: isBasic },
        { href: "/jobs", title: "Jobs", icon: Briefcase, show: isBasic || isCustomerOnly },
        { href: "/dashboard", title: "Job History", icon: LayoutDashboard, show: isBasic },
        { href: "/feeds", title: "RSS Feeds", icon: Rss, show: isBasic },
        { href: "/ats-config", title: "ATS Config", icon: Cpu, show: isBasic },
        // Admin only
        { href: "/admin/users", title: "User Mgmt", icon: Users, show: isAdmin },
        // Settings visible only to basic+ users
        { href: "/settings", title: "Settings", icon: Settings, show: isBasic },
    ];

    return (
        <div className={cn("pb-12 min-h-screen border-r border-border bg-sidebar text-sidebar-foreground w-64 hidden md:flex flex-col", className)} {...props}>
            <div className="space-y-4 py-4 flex-1">
                <div className="px-3 py-2">
                    <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight text-primary flex items-center gap-2">
                        AutoApply <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">{user?.username}</span>
                    </h2>
                    <div className="space-y-1">
                        {items.filter(i => i.show).map((item) => (
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

            <div className="px-3 py-4 border-t">
                <button
                    onClick={logout}
                    className="flex w-full items-center rounded-md px-3 py-2 text-sm font-medium text-red-500 hover:bg-red-50 hover:text-red-600 transition-colors"
                >
                    <LogOut className="mr-2 h-4 w-4" />
                    Sign Out
                </button>
            </div>
        </div>
    );
}
