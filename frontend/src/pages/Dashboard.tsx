import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Cell } from 'recharts';
import { Activity, AlertTriangle, BellRing, Gauge, TrendingUp, Zap } from 'lucide-react';
import * as api from '../api/client';

const RISK_COLORS = { CRITICAL: '#dc2626', HIGH: '#ea580c', MODERATE: '#d97706', LOW: '#16a34a' };
const PIE_COLORS = ['#2563eb', '#4f46e5', '#0891b2', '#059669', '#d97706', '#dc2626'];

export default function DashboardPage() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [wsStatus, setWsStatus] = useState('Connecting...');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoResult, setDemoResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      const [m, t, e, p, h] = await Promise.all([
        api.fetchRiskOverview().catch(() => null),
        api.fetchRiskTimeline().catch(() => []),
        api.fetchEvents({ page_size: 5 }).catch(() => ({ items: [] })),
        api.fetchPortfolioExposure().catch(() => null),
        api.fetchHealth().catch(() => null),
      ]);
      setMetrics(m);
      setTimeline(t);
      setEvents(e.items || []);
      setPortfolio(p);
      setHealth(h);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    const ws = api.createWebSocket(
      (data) => {
        setEvents(prev => [data, ...prev].slice(0, 5));
        loadData(); // Refresh metrics
      },
      setWsStatus,
    );
    return () => ws.close();
  }, [loadData]);

  const handleRunDemo = async () => {
    setDemoRunning(true);
    setDemoResult(null);
    try {
      const result = await api.runDemo();
      setDemoResult(result);
      await loadData();
    } catch (err: any) {
      setDemoResult({ success: false, error: err.message });
    } finally {
      setDemoRunning(false);
    }
  };

  if (loading) return <div className="loading-state"><div className="spinner" /><p>Loading dashboard...</p></div>;
  if (error && !metrics) return (
    <div className="error-state">
      <AlertTriangle size={48} />
      <p>{error}</p>
      <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={loadData}>Retry</button>
    </div>
  );

  const riskLevel = (metrics?.overall_risk ?? 0) >= 7 ? 'CRITICAL' : (metrics?.overall_risk ?? 0) >= 5 ? 'HIGH' : (metrics?.overall_risk ?? 0) >= 3 ? 'MODERATE' : 'LOW';

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Risk Command Center</h1>
          <div className="page-header-sub">AI-Powered Financial Risk Intelligence</div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span className={`risk-badge ${wsStatus === 'LIVE' ? 'low' : 'moderate'}`}>
            ● {wsStatus}
          </span>
          <button className="btn btn-primary" onClick={handleRunDemo} disabled={demoRunning} id="run-demo-btn">
            <Zap size={16} />
            {demoRunning ? 'Running...' : 'Run Demo'}
          </button>
        </div>
      </div>

      {/* Demo result */}
      {demoResult && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <div className="card-header"><span className="card-title">Demo Pipeline Result</span></div>
          <div className="card-body">
            <div className="demo-steps">
              {(demoResult.steps || []).map((step: any) => (
                <div key={step.step} className={`demo-step ${step.status}`}>
                  <div className="demo-step-num">{step.step}</div>
                  <div><strong>{step.name}</strong>: {step.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="kpi-grid" style={{ marginBottom: '1.5rem' }}>
        {[
          { label: 'Overall Risk', value: `${metrics?.overall_risk?.toFixed(1) ?? '—'} / 10`, sub: metrics?.market_risk ?? '—', icon: Gauge },
          { label: 'High Risk Events', value: metrics?.high_risk_events ?? 0, icon: AlertTriangle },
          { label: 'Critical Events', value: metrics?.critical_events ?? 0, icon: BellRing },
          { label: 'Avg Sentiment', value: metrics?.average_sentiment?.toFixed(3) ?? '—', icon: TrendingUp },
          { label: 'Events Processed', value: metrics?.events_processed ?? 0, icon: Activity },
        ].map(({ label, value, sub, icon: Icon }) => (
          <div key={label} className="kpi-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span className="kpi-label">{label}</span>
              <Icon size={16} style={{ color: 'var(--text-tertiary)' }} />
            </div>
            <div className="kpi-value">{value}</div>
            {sub && <div className="kpi-sub">{sub}</div>}
          </div>
        ))}
      </div>

      {/* Risk Timeline + Stress Trigger */}
      <div className="grid-12" style={{ marginBottom: '1.5rem' }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Risk Trajectory</span>
            <span className={`risk-badge ${riskLevel.toLowerCase()}`}>{riskLevel}</span>
          </div>
          <div className="card-body">
            {timeline.length > 0 ? (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline}>
                    <defs>
                      <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#2563eb" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#2563eb" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} tickFormatter={(v) => new Date(v).toLocaleTimeString()} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} />
                    <Tooltip labelFormatter={(v) => new Date(v).toLocaleString()} />
                    <Area type="monotone" dataKey="risk" stroke="#2563eb" fill="url(#riskGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="empty-state"><p>No risk data yet. Run the demo to generate events.</p></div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Portfolio Exposure</span></div>
          <div className="card-body">
            {portfolio?.by_asset_class?.length > 0 ? (
              <>
                <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>Total Value</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>${((portfolio?.total_value ?? 0) / 1e6).toFixed(1)}M</div>
                  {portfolio?.is_synthetic && <div style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>Synthetic Portfolio</div>}
                </div>
                <div style={{ height: 160 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={portfolio.by_asset_class} dataKey="value" nameKey="asset_class" cx="50%" cy="50%" outerRadius={60} label={({ asset_class, weight }) => `${asset_class} ${weight}%`} labelLine={false} fontSize={9}>
                        {portfolio.by_asset_class.map((_: any, i: number) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v: number) => `$${(v / 1e6).toFixed(1)}M`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </>
            ) : (
              <div className="empty-state"><p>Portfolio loading...</p></div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Events + Model Status */}
      <div className="grid-12">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Recent Risk Events</span>
            <button className="btn btn-sm btn-secondary" onClick={() => navigate('/events')}>View All</button>
          </div>
          <div className="card-body">
            {events.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {events.map((evt, i) => (
                  <div key={evt.signal_id || i} className="event-card" onClick={() => evt.signal_id && navigate(`/events/${evt.signal_id}`)}>
                    <div className="event-card-header">
                      <div className="event-card-source">{evt.source?.name ?? 'Unknown'}</div>
                      <span className={`risk-badge ${(evt.impact?.risk_level ?? 'low').toLowerCase()}`}>
                        {evt.impact?.risk_level ?? 'LOW'}
                      </span>
                    </div>
                    <div className="event-card-text">{evt.text?.slice(0, 150)}{evt.text?.length > 150 ? '...' : ''}</div>
                    <div className="event-card-tags">
                      <span className="tag">Impact: {evt.impact?.score ?? 0}</span>
                      <span className="tag">Event: {evt.event?.class ?? '—'}</span>
                      <span className="tag">Sentiment: {evt.sentiment?.label ?? '—'}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state"><p>No events yet. Click "Run Demo" to generate events.</p></div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">System Status</span></div>
          <div className="card-body">
            {health ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <StatusRow label="Database" value={health.database} />
                <StatusRow label="Redis" value={health.redis} />
                <StatusRow label="FinBERT" value={health.models?.finbert} />
                <StatusRow label="Embeddings" value={health.models?.embedding_model} />
                <StatusRow label="Classifier" value={health.models?.event_classifier} />
                <StatusRow label="WebSocket" value={wsStatus === 'LIVE' ? 'connected' : wsStatus} />
              </div>
            ) : (
              <div className="empty-state"><p>Unable to reach backend</p></div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function StatusRow({ label, value }: { label: string; value?: string }) {
  const isOk = value === 'ready' || value === 'connected' || value === 'LIVE';
  const isWarn = value?.startsWith('error') || value === 'unavailable';
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0.6rem', background: 'var(--bg-tertiary)', borderRadius: 6, fontSize: '0.8rem' }}>
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontWeight: 500, color: isOk ? 'var(--risk-low)' : isWarn ? 'var(--risk-critical)' : 'var(--text-tertiary)' }}>
        {value ?? 'unknown'}
      </span>
    </div>
  );
}
