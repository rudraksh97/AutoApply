import { Link, useLocation } from 'react-router-dom';
import { Rss, Briefcase, User, Settings, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { path: '/feeds', label: 'RSS Feeds', icon: Rss },
  { path: '/jobs', label: 'Job History', icon: Briefcase },
  { path: '/profile', label: 'My Profile', icon: User },
  { path: '/ats-config', label: 'ATS Configuration', icon: FileText },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ className }: { className?: string }) {
  const location = useLocation();

  return (
    <aside className={cn("w-64 bg-[#0C2C55] border-r border-[#296374] flex flex-col", className)}>
      <div className="p-6 border-b border-[#296374]">
        <h1 className="text-xl font-semibold text-[#E8E2DB]">AutoApply 🚀</h1>
      </div>
      
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            // Active if exact match or subpath
            const isActive = location.pathname.startsWith(item.path);
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
                    isActive
                      ? "bg-[#E8E2DB] text-[#0C2C55]"
                      : "text-[#E8E2DB] hover:bg-[#E8E2DB]/20"
                  )}
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
