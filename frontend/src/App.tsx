import { useState } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import {
  Activity, AlertTriangle, BarChart3, Briefcase, FileText,
  LayoutDashboard, Radio, Search, Settings, ShieldAlert,
  TrendingUp, Users, Zap, Menu, X
} from 'lucide-react';

import DashboardPage from './pages/Dashboard';
import LiveFeedPage from './pages/LiveFeed';
import EventsPage from './pages/Events';
import EventDetailPage from './pages/EventDetail';
import EntitiesPage from './pages/Entities';
import EntityDetailPage from './pages/EntityDetail';
import PortfolioPage from './pages/Portfolio';
import StressTestingPage from './pages/StressTesting';
import AnalyticsPage from './pages/Analytics';
import SettingsPage from './pages/SettingsPage';

const navItems = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard },
  { label: 'Live Feed', to: '/live-feed', icon: Radio },
  { label: 'Events', to: '/events', icon: FileText },
  { label: 'Entities', to: '/entities', icon: Users },
  { label: 'Portfolio', to: '/portfolio', icon: Briefcase },
  { label: 'Stress Testing', to: '/stress-testing', icon: Zap },
  { label: 'Analytics', to: '/analytics', icon: BarChart3 },
  { label: 'Settings', to: '/settings', icon: Settings },
];

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      {/* Mobile menu button */}
      <button
        className="btn btn-secondary"
        style={{ position: 'fixed', top: 12, left: 12, zIndex: 50, display: 'none' }}
        onClick={() => setSidebarOpen(!sidebarOpen)}
        id="mobile-menu-btn"
      >
        {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <ShieldAlert size={18} />
          </div>
          <div className="sidebar-brand-text">
            <span>FinRisk</span>
            <span>Intelligence</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(({ label, to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setSidebarOpen(false)}
            >
              <Icon />
              {label}
            </NavLink>
          ))}
        </nav>
        <div style={{ padding: '1rem', borderTop: '1px solid rgba(255,255,255,0.08)', fontSize: '0.7rem', color: 'var(--text-on-dark-muted)' }}>
          AI-Powered Risk Platform
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/live-feed" element={<LiveFeedPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/events/:eventId" element={<EventDetailPage />} />
          <Route path="/entities" element={<EntitiesPage />} />
          <Route path="/entities/:entityId" element={<EntityDetailPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/stress-testing" element={<StressTestingPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
