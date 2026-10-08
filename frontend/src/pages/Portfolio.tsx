import { useEffect, useState } from 'react';
import { Briefcase } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import * as api from '../api/client';

const COLORS = ['#2563eb', '#4f46e5', '#0891b2', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0d9488'];

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadPortfolio = () => {
    setLoading(true);
    setError('');
    api.fetchPortfolioExposure()
      .then(setPortfolio)
      .catch((err) => setError(err.message || 'Unable to load portfolio data'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadPortfolio();
  }, []);

  if (loading) return <div className="loading-state"><div className="spinner" /></div>;
  if (error || !portfolio) return (
    <div className="error-state">
      <p>{error || 'Unable to load portfolio data'}</p>
      <button className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }} onClick={loadPortfolio}>Retry</button>
    </div>
  );

  const byClass = portfolio.by_asset_class || [];
  const bySector = portfolio.by_sector || [];
  const positions = portfolio.positions || [];

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Portfolio</h1>
          <div className="page-header-sub">{portfolio.name || 'Wholesale Banking Portfolio'}</div>
        </div>
        {portfolio.is_synthetic && <span className="tag" style={{ background: '#fffbeb', color: '#d97706' }}>Synthetic Portfolio</span>}
      </div>

      {/* KPIs */}
      <div className="kpi-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="kpi-card">
          <div className="kpi-label">Total Value</div>
          <div className="kpi-value">${((portfolio.total_value || 0) / 1e6).toFixed(1)}M</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Asset Classes</div>
          <div className="kpi-value">{byClass.length}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Positions</div>
          <div className="kpi-value">{positions.length}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Sectors</div>
          <div className="kpi-value">{bySector.length}</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        <div className="card">
          <div className="card-header"><span className="card-title">Asset Allocation</span></div>
          <div className="card-body">
            <div style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={byClass} dataKey="value" nameKey="asset_class" cx="50%" cy="50%" outerRadius={100} innerRadius={50}
                    label={({ asset_class, weight }) => `${asset_class} ${weight}%`} labelLine fontSize={11}>
                    {byClass.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => `$${(v / 1e6).toFixed(1)}M`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Sector Exposure</span></div>
          <div className="card-body">
            <div style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bySector} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" tickFormatter={v => `$${(v / 1e6).toFixed(0)}M`} tick={{ fontSize: 11 }} />
                  <YAxis dataKey="sector" type="category" width={100} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => `$${(v / 1e6).toFixed(1)}M`} />
                  <Bar dataKey="value" fill="#4f46e5" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Positions table */}
      <div className="card">
        <div className="card-header"><span className="card-title">All Positions</span></div>
        <div className="card-body" style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset ID</th>
                <th>Class</th>
                <th>Issuer</th>
                <th>Ticker</th>
                <th>Notional</th>
                <th>Sector</th>
                <th>Country</th>
                <th>Duration</th>
                <th>Credit</th>
                <th>Risk Wt</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p: any, i: number) => (
                <tr key={p.asset_id || i} style={{ cursor: 'default' }}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{p.asset_id}</td>
                  <td><span className="tag">{p.asset_class}</span></td>
                  <td>{p.issuer}</td>
                  <td style={{ fontWeight: 500 }}>{p.ticker || '—'}</td>
                  <td style={{ fontWeight: 600 }}>${((p.notional || p.value || 0) / 1e6).toFixed(1)}M</td>
                  <td>{p.sector || '—'}</td>
                  <td>{p.country || '—'}</td>
                  <td>{p.duration != null ? `${p.duration}yr` : '—'}</td>
                  <td>{p.credit_quality || '—'}</td>
                  <td>{p.risk_weight?.toFixed(2) ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
