import React from 'react';
import { ShieldCheck, Activity, Database, AlertTriangle, RefreshCw, GitCommit } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  systemStatus: string;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  systemStatus,
  onRefresh,
  isRefreshing,
}) => {
  const navItems = [
    { id: 'overview', label: 'Platform Overview', icon: Activity },
    { id: 'pipelines', label: 'Pipelines & Runs', icon: Database },
    { id: 'quality', label: 'Data Quality & Drift', icon: ShieldCheck },
    { id: 'incidents', label: 'Failure Incidents', icon: AlertTriangle },
    { id: 'recovery', label: 'Healing & Audit', icon: GitCommit },
  ];

  return (
    <header style={{ backgroundColor: '#0f172a', borderBottom: '1px solid #334155', padding: '0.75rem 1.5rem' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            background: 'linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)',
            padding: '0.5rem',
            borderRadius: '0.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#0f172a'
          }}>
            <ShieldCheck size={24} strokeWidth={2.5} />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.025em', color: '#f8fafc' }}>
              Self-Healing Data Platform
            </h1>
            <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8' }}>
              Autonomous Ingestion • Quality Gates • Zero-Defect Recovery
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '0.5rem' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 0.85rem',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: isActive ? '#38bdf8' : 'transparent',
                  color: isActive ? '#0f172a' : '#cbd5e1',
                  transition: 'all 0.15s ease',
                }}
              >
                <Icon size={16} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* System Health Status & Manual Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            backgroundColor: '#1e293b',
            padding: '0.35rem 0.75rem',
            borderRadius: '9999px',
            fontSize: '0.75rem',
            border: '1px solid #334155'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: systemStatus === 'UP' ? '#10b981' : '#f59e0b'
            }} />
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>API: {systemStatus}</span>
          </div>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Refresh Platform Telemetry"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '0.375rem',
              color: '#94a3b8',
              padding: '0.5rem',
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={16} style={{ animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }} />
          </button>
        </div>
      </div>
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </header>
  );
};

