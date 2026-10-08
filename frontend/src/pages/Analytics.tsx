import { useEffect, useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import * as api from '../api/client';

const COLORS = ['#2563eb', '#4f46e5', '#0891b2', '#059669', '#d97706', '#dc2626', '#7c3aed', '#f59e0b'];

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadAnalytics = () => {
    setLoading(true);
    setError('');
    api.fetchAnalytics()
      .then(setData)
      .catch((err) => setError(err.message || 'Unable to load analytics'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  if (loading) return <div className="loading-state"><div className="spinner" /></div>;
  if (error || !data) return (
    <div className="error-state">
      <p>{error || 'Unable to load analytics'}</p>
      <button className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }} onClick={loadAnalytics}>Retry</button>
    </div>
  );

  const eventDist = Object.entries(data.event_distribution || {}).map(([k, v]) => ({ name: k, value: v as number }));
  const sentDist = Object.entries(data.sentiment_distribution || {}).map(([k, v]) => ({ name: k, value: v as number }));
  const riskDist = Object.entries(data.risk_distribution || {}).map(([k, v]) => ({ name: k, value: v as number }));
  const sourceDist = Object.entries(data.source_distribution || {}).map(([k, v]) => ({ name: k, value: v as number }));

  const riskColors: Record<string, string> = { CRITICAL: '#dc2626', HIGH: '#ea580c', MODERATE: '#d97706', LOW: '#16a34a' };
  const sentColors: Record<string, string> = { positive: '#16a34a', negative: '#dc2626', neutral: '#6b7280' };

  return (
    <>
      <div className="page-header"><h1>Analytics</h1></div>

      {/* KPIs */}
      <div className="kpi-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="kpi-card"><div className="kpi-label">Events Processed</div><div className="kpi-value">{data.events_processed}</div></div>
        <div className="kpi-card"><div className="kpi-label">Overall Risk</div><div className="kpi-value">{data.overall_risk?.toFixed(1)}/10</div><div className="kpi-sub">{data.market_risk}</div></div>
        <div className="kpi-card"><div className="kpi-label">High Risk</div><div className="kpi-value">{data.high_risk_events}</div></div>
        <div className="kpi-card"><div className="kpi-label">Critical</div><div className="kpi-value">{data.critical_events}</div></div>
        <div className="kpi-card"><div className="kpi-label">Avg Sentiment</div><div className="kpi-value">{data.average_sentiment?.toFixed(3)}</div></div>
        <div className="kpi-card"><div className="kpi-label">Avg Impact</div><div className="kpi-value">{data.average_impact?.toFixed(2)}</div></div>
      </div>

      {/* Charts */}
      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        <div className="card">
          <div className="card-header"><span className="card-title">Event Distribution</span></div>
          <div className="card-body">
            {eventDist.length > 0 ? (
              <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={eventDist} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#2563eb" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <div className="empty-state"><p>No data</p></div>}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Risk Distribution</span></div>
          <div className="card-body">
            {riskDist.length > 0 ? (
              <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={riskDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, value }) => `${name}: ${value}`} fontSize={11}>
                      {riskDist.map((d, i) => <Cell key={i} fill={riskColors[d.name] || COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : <div className="empty-state"><p>No data</p></div>}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><span className="card-title">Sentiment Distribution</span></div>
          <div className="card-body">
            {sentDist.length > 0 ? (
              <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={sentDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} innerRadius={50} label fontSize={11}>
                      {sentDist.map((d, i) => <Cell key={i} fill={sentColors[d.name] || COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : <div className="empty-state"><p>No data</p></div>}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Source Distribution</span></div>
          <div className="card-body">
            {sourceDist.length > 0 ? (
              <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sourceDist}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <div className="empty-state"><p>No data</p></div>}
          </div>
        </div>
      </div>
    </>
  );
}
