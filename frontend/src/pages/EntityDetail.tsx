import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Line, LineChart } from 'recharts';
import * as api from '../api/client';

export default function EntityDetailPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!entityId) return;
    api.fetchEntity(entityId)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [entityId]);

  if (loading) return <div className="loading-state"><div className="spinner" /></div>;
  if (error || !data) return (
    <div className="error-state"><p>{error || 'Entity not found'}</p>
      <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={() => navigate('/entities')}>Back</button>
    </div>
  );

  const entity = data.entity || {};

  return (
    <>
      <button className="btn btn-secondary btn-sm" onClick={() => navigate('/entities')} style={{ marginBottom: '1rem' }}>
        <ArrowLeft size={16} /> Back to Entities
      </button>

      <div className="page-header">
        <div>
          <h1>{entity.canonical_name} {entity.ticker ? `(${entity.ticker})` : ''}</h1>
          <div className="page-header-sub">{entity.entity_type} · {entity.event_count} events</div>
        </div>
      </div>

      {/* Overview KPIs */}
      <div className="kpi-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="kpi-card"><div className="kpi-label">Avg Risk</div><div className="kpi-value">{entity.avg_risk?.toFixed(1) ?? '—'}</div></div>
        <div className="kpi-card"><div className="kpi-label">Avg Sentiment</div><div className="kpi-value">{entity.avg_sentiment?.toFixed(3) ?? '—'}</div></div>
        <div className="kpi-card"><div className="kpi-label">Events</div><div className="kpi-value">{entity.event_count ?? 0}</div></div>
        <div className="kpi-card"><div className="kpi-label">Last Seen</div><div className="kpi-value" style={{ fontSize: '0.9rem' }}>{entity.last_seen ? new Date(entity.last_seen).toLocaleDateString() : '—'}</div></div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        {/* Risk timeline */}
        <div className="card">
          <div className="card-header"><span className="card-title">Risk Timeline</span></div>
          <div className="card-body">
            {data.risk_timeline?.length > 0 ? (
              <div className="chart-container" style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.risk_timeline}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} tickFormatter={v => new Date(v).toLocaleTimeString()} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 10 }} />
                    <Tooltip labelFormatter={v => new Date(v).toLocaleString()} />
                    <Area type="monotone" dataKey="risk" stroke="#2563eb" fill="#2563eb" fillOpacity={0.15} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : <div className="empty-state"><p>No risk data</p></div>}
          </div>
        </div>

        {/* Sentiment timeline */}
        <div className="card">
          <div className="card-header"><span className="card-title">Sentiment Timeline</span></div>
          <div className="card-body">
            {data.sentiment_timeline?.length > 0 ? (
              <div className="chart-container" style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.sentiment_timeline}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} tickFormatter={v => new Date(v).toLocaleTimeString()} />
                    <YAxis domain={[-1, 1]} tick={{ fontSize: 10 }} />
                    <Tooltip labelFormatter={v => new Date(v).toLocaleString()} />
                    <Line type="monotone" dataKey="sentiment" stroke="#059669" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : <div className="empty-state"><p>No sentiment data</p></div>}
          </div>
        </div>
      </div>

      {/* Event History */}
      <div className="card">
        <div className="card-header"><span className="card-title">Event History</span></div>
        <div className="card-body">
          {data.events?.length > 0 ? (
            <table className="data-table">
              <thead><tr><th>Time</th><th>Event</th><th>Impact</th><th>Risk</th><th>Sentiment</th></tr></thead>
              <tbody>
                {data.events.map((evt: any, i: number) => (
                  <tr key={evt.signal_id || i} onClick={() => navigate(`/events/${evt.signal_id}`)}>
                    <td style={{ fontSize: '0.75rem' }}>{evt.timestamp ? new Date(evt.timestamp).toLocaleString() : '—'}</td>
                    <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{evt.text?.slice(0, 80)}...</td>
                    <td style={{ fontWeight: 600 }}>{evt.impact_score}</td>
                    <td><span className={`risk-badge ${(evt.risk_level ?? 'low').toLowerCase()}`}>{evt.risk_level}</span></td>
                    <td style={{ color: evt.sentiment_label === 'negative' ? 'var(--sentiment-negative)' : evt.sentiment_label === 'positive' ? 'var(--sentiment-positive)' : 'inherit' }}>
                      {evt.sentiment_label} ({evt.sentiment_score?.toFixed(2)})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <div className="empty-state"><p>No events for this entity</p></div>}
        </div>
      </div>
    </>
  );
}
