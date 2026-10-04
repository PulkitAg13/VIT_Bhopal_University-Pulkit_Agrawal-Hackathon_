import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Search } from 'lucide-react';
import * as api from '../api/client';

export default function EntitiesPage() {
  const navigate = useNavigate();
  const [entities, setEntities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.fetchEntities(search || undefined);
      setEntities(res.items || []);
    } catch { setEntities([]); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const riskClass = (r: number) => r >= 8 ? 'critical' : r >= 6 ? 'high' : r >= 4 ? 'moderate' : 'low';

  return (
    <>
      <div className="page-header"><h1>Entity Risk Monitor</h1></div>

      <div className="filter-bar">
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)' }} />
          <input className="input" style={{ paddingLeft: 32, width: '100%' }} placeholder="Search entities..."
            value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && load()} />
        </div>
        <button className="btn btn-secondary btn-sm" onClick={load}>Search</button>
      </div>

      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : entities.length > 0 ? (
        <div className="card">
          <table className="data-table">
            <thead>
              <tr>
                <th>Entity</th>
                <th>Ticker</th>
                <th>Type</th>
                <th>Current Risk</th>
                <th>Avg Sentiment</th>
                <th>Events</th>
                <th>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {entities.map((e, i) => (
                <tr key={e.id || i} onClick={() => navigate(`/entities/${encodeURIComponent(e.canonical_name || e.id)}`)}>
                  <td style={{ fontWeight: 500 }}>{e.canonical_name}</td>
                  <td>{e.ticker || '—'}</td>
                  <td><span className="tag">{e.entity_type}</span></td>
                  <td><span className={`risk-badge ${riskClass(e.avg_risk)}`}>{e.avg_risk?.toFixed(1)}</span></td>
                  <td style={{ color: e.avg_sentiment < -0.1 ? 'var(--sentiment-negative)' : e.avg_sentiment > 0.1 ? 'var(--sentiment-positive)' : 'var(--sentiment-neutral)' }}>
                    {e.avg_sentiment?.toFixed(3)}
                  </td>
                  <td>{e.event_count}</td>
                  <td style={{ fontSize: '0.75rem' }}>{e.last_seen ? new Date(e.last_seen).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state"><Users size={48} /><p>No entities found. Process some events first.</p></div>
      )}
    </>
  );
}
