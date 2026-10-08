import { useEffect, useState } from 'react';
import { Zap, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import * as api from '../api/client';

export default function StressTestingPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [selected, setSelected] = useState('GEOPOLITICAL_SHOCK');
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadStressData = () => {
    setLoading(true);
    setError('');
    Promise.all([
      api.fetchStressScenarios(),
      api.fetchStressResults(),
    ])
      .then(([s, r]) => {
        setScenarios(s.scenarios || []);
        setResults(r.results || []);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load stress test data');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadStressData();
  }, []);

  const handleRun = async () => {
    setRunning(true);
    try {
      const result = await api.runStressTest(selected);
      setLastResult(result);
      // Refresh results
      const r = await api.fetchStressResults();
      setResults(r.results || []);
    } catch (err: any) {
      setLastResult({ error: err.message });
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <div className="loading-state"><div className="spinner" /></div>;
  if (error) return (
    <div className="error-state">
      <AlertTriangle size={48} style={{ color: 'var(--risk-critical)' }} />
      <p>{error}</p>
      <button className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }} onClick={loadStressData}>Retry</button>
    </div>
  );

  const impactData = (lastResult?.asset_level_impacts || []).map((a: any) => ({
    name: a.asset_class,
    impact: a.impact_pct,
    before: a.before_value,
    after: a.after_value,
  }));

  return (
    <>
      <div className="page-header">
        <h1>Stress Testing</h1>
      </div>

      {/* Run stress test */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header"><span className="card-title">Run Stress Test</span></div>
        <div className="card-body">
          <div className="filter-bar">
            <select className="select" value={selected} onChange={e => setSelected(e.target.value)} style={{ minWidth: 220 }}>
              {scenarios.map(s => <option key={s.name} value={s.name}>{s.name} — {s.description}</option>)}
            </select>
            <button className="btn btn-primary" onClick={handleRun} disabled={running} id="run-stress-btn">
              <Zap size={16} />
              {running ? 'Running...' : 'Run Stress Test'}
            </button>
          </div>

          {/* Selected scenario details */}
          {scenarios.find(s => s.name === selected) && (
            <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'var(--bg-tertiary)', borderRadius: 8, fontSize: '0.8rem' }}>
              <strong>Assumptions:</strong> {scenarios.find(s => s.name === selected)?.assumptions}
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {Object.entries(scenarios.find(s => s.name === selected)?.parameters || {}).map(([k, v]) => (
                  <span key={k} className="tag">{k}: {typeof v === 'number' ? `${(v as number * 100).toFixed(1)}%` : String(v)}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Last result */}
      {lastResult && !lastResult.error && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <span className="card-title">Result: {lastResult.scenario}</span>
            <span className={`risk-badge ${lastResult.loss_percentage > 10 ? 'critical' : lastResult.loss_percentage > 5 ? 'high' : 'moderate'}`}>
              {lastResult.loss_percentage?.toFixed(1)}% Loss
            </span>
          </div>
          <div className="card-body">
            <div className="kpi-grid" style={{ marginBottom: '1rem' }}>
              <div className="kpi-card"><div className="kpi-label">Before</div><div className="kpi-value">${(lastResult.portfolio_before / 1e6).toFixed(1)}M</div></div>
              <div className="kpi-card"><div className="kpi-label">After</div><div className="kpi-value">${(lastResult.portfolio_after / 1e6).toFixed(1)}M</div></div>
              <div className="kpi-card"><div className="kpi-label">Loss</div><div className="kpi-value" style={{ color: 'var(--risk-critical)' }}>-${(lastResult.absolute_loss / 1e6).toFixed(1)}M</div></div>
              <div className="kpi-card"><div className="kpi-label">Loss %</div><div className="kpi-value" style={{ color: 'var(--risk-critical)' }}>-{lastResult.loss_percentage?.toFixed(2)}%</div></div>
            </div>

            {/* Impact chart */}
            {impactData.length > 0 && (
              <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={impactData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
                    <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => `${v.toFixed(2)}%`} />
                    <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
                      {impactData.map((d: any, i: number) => (
                        <Cell key={i} fill={d.impact < 0 ? '#dc2626' : d.impact > 0 ? '#16a34a' : '#6b7280'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Asset-level table */}
            <table className="data-table" style={{ marginTop: '1rem' }}>
              <thead><tr><th>Asset Class</th><th>Before</th><th>After</th><th>Impact</th><th>Impact %</th></tr></thead>
              <tbody>
                {(lastResult.asset_level_impacts || []).map((a: any, i: number) => (
                  <tr key={i} style={{ cursor: 'default' }}>
                    <td>{a.asset_class}</td>
                    <td>${(a.before_value / 1e6).toFixed(2)}M</td>
                    <td>${(a.after_value / 1e6).toFixed(2)}M</td>
                    <td style={{ color: a.impact < 0 ? 'var(--risk-critical)' : a.impact > 0 ? 'var(--risk-low)' : 'inherit', fontWeight: 600 }}>
                      {a.impact >= 0 ? '+' : ''}${(a.impact / 1e6).toFixed(3)}M
                    </td>
                    <td style={{ color: a.impact_pct < 0 ? 'var(--risk-critical)' : a.impact_pct > 0 ? 'var(--risk-low)' : 'inherit' }}>
                      {a.impact_pct >= 0 ? '+' : ''}{a.impact_pct?.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {lastResult?.error && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-body" style={{ color: 'var(--risk-critical)' }}>Error: {lastResult.error}</div>
        </div>
      )}

      {/* History */}
      {results.length > 0 && (
        <div className="card">
          <div className="card-header"><span className="card-title">Stress Test History</span></div>
          <div className="card-body">
            <table className="data-table">
              <thead><tr><th>Time</th><th>Scenario</th><th>Before</th><th>After</th><th>Loss</th><th>Auto</th></tr></thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={r.simulation_id || i} style={{ cursor: 'default' }}>
                    <td style={{ fontSize: '0.75rem' }}>{r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'}</td>
                    <td><span className="tag">{r.scenario}</span></td>
                    <td>${(r.portfolio_before / 1e6).toFixed(1)}M</td>
                    <td>${(r.portfolio_after / 1e6).toFixed(1)}M</td>
                    <td style={{ color: 'var(--risk-critical)', fontWeight: 500 }}>-{r.loss_percentage?.toFixed(1)}%</td>
                    <td>{r.is_auto_triggered ? '⚡ Auto' : 'Manual'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
