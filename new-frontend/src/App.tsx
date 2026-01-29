import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { Sidebar } from "./components/layout/Sidebar";
import RssFeedsPage from "./pages/feeds/Page";
import JobsPage from "./pages/jobs/Page";
import ProfilePage from "./pages/profile/Page";
import AtsConfigPage from "./pages/ats-config/Page";
import SettingsPage from "./pages/settings/Page";

import { Toaster } from 'sonner';

export default function App() {
  return (
    <Router>
      <div className="flex h-screen bg-background text-foreground font-sans">
        <Sidebar className="flex-none" />
        <main className="flex-1 overflow-auto bg-background relative">
           <Routes>
            <Route path="/" element={<Navigate to="/feeds" replace />} />
            <Route path="/feeds" element={<RssFeedsPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/ats-config" element={<AtsConfigPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
        <Toaster />
      </div>
    </Router>
  );
}
