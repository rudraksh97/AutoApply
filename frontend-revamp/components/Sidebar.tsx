"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Rss, History, User, Settings, FileText } from 'lucide-react';

const navItems = [
  { path: '/rss-feeds', label: 'RSS Feeds', icon: Rss },
  { path: '/job-history', label: 'Job History', icon: History },
  { path: '/my-profile', label: 'My Profile', icon: User },
  { path: '/ats-config', label: 'ATS Configuration', icon: FileText },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-[#0C2C55] border-r border-[#296374] flex flex-col">
      <div className="p-6 border-b border-[#296374]">
        <h1 className="text-xl font-semibold text-[#E8E2DB]">AutoApply</h1>
      </div>
      
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.path;
            
            return (
              <li key={item.path}>
                <Link
                  href={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-[#E8E2DB] text-[#0C2C55]'
                      : 'text-[#E8E2DB] hover:bg-[#E8E2DB]/20'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}