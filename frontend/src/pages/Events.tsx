import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Search } from 'lucide-react';
import * as api from '../api/client';

export default function EventsPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');

  const loadEvents = async () => {
    setLoading(true);
    try {
      const params: api.EventsParams = { page, page_size: 25 };
      if (search) params.search = search;
      if (classFilter) params.event_class = classFilter;
      if (riskFilter) params.risk_level = riskFilter;
      const res = await api.fetchEvents(params);
      setEvents(res.items || []);
      setTotal(res.count || 0);
    } catch { setEvents([]); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadEvents(); }, [page, classFilter, riskFilter]);

  return (
    <>
      <div className="page-header">
        <h1>Events ({total})</h1>
      </div>

      <div className="filter-bar">
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)' }} />
          <input className="input" style={{ paddingLeft: 32, width: '100%' }} placeholder="Search events..." value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && loadEvents()} />
        </div>
        <select className="select" value={classFilter} onChange={e => { setClassFilter(e.target.value); setPage(1); }}>
          <option value="">All Classes</option>
          {['Geopolitical','Macroeconomic','Credit Event','Earnings','Regulatory / Legal','Monetary Policy','Commodity / Energy','Liquidity','Supply Chain','Market Movement'].map(c =>
            <option key={c} value={c}>{c}</option>
          )}
        </select>
        <select className="select" value={riskFilter} onChange={e => { setRiskFilter(e.target.value); setPage(1); }}>
          <option value="">All Risk</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MODERATE">Moderate</option>
          <option value="LOW">Low</option>
        </select>
        <button className="btn btn-secondary btn-sm" onClick={loadEvents}>Search</button>
      </div>

      {loading ? (
        <div className="loading-state"><div className="spinner" /></div>
      ) : events.length > 0 ? (
        <>
          <div className="card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Entity</th>
                  <th>Event Class</th>
                  <th>Sentiment</th>
                  <th>Impact</th>
                  <th>Risk</th>
                  <th>Confidence</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {events.map((evt, i) => (
                  <tr key={evt.signal_id || i} onClick={() => evt.signal_id && navigate(`/events/${evt.signal_id}`)}>
                    <td style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>{evt.timestamp ? new Date(evt.timestamp).toLocaleString() : '—'}</td>
                    <td>{evt.entities?.[0]?.canonical_name ?? evt.entities?.[0]?.name ?? '—'}</td>
                    <td><span className="tag">{evt.event?.class ?? '—'}</span></td>
                    <td style={{ color: evt.sentiment?.label === 'negative' ? 'var(--sentiment-negative)' : evt.sentiment?.label === 'positive' ? 'var(--sentiment-positive)' : 'var(--sentiment-neutral)' }}>
                      {evt.sentiment?.label ?? '—'} ({evt.sentiment?.score?.toFixed(2) ?? '0'})
                    </td>
                    <td style={{ fontWeight: 600 }}>{evt.impact?.score ?? 0}</td>
                    <td><span className={`risk-badge ${(evt.impact?.risk_level ?? 'low').toLowerCase()}`}>{evt.impact?.risk_level ?? 'LOW'}</span></td>
                    <td>{(evt.confidence_score ?? 0).toFixed(2)}</td>
                    <td style={{ fontSize: '0.75rem' }}>{evt.source?.name ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginTop: '1rem' }}>
            <button className="btn btn-sm btn-secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
            <span style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}>Page {page} of {Math.ceil(total / 25)}</span>
            <button className="btn btn-sm btn-secondary" disabled={page * 25 >= total} onClick={() => setPage(p => p + 1)}>Next</button>
          </div>
        </>
      ) : (
        <div className="empty-state">
          <FileText size={48} />
          <p>No events found. Use the Live Feed to ingest data.</p>
        </div>
      )}
    </>
  );
}
