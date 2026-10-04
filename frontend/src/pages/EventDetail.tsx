import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import * as api from '../api/client';

export default function EventDetailPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();
  const [event, setEvent] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!eventId) return;
    api.fetchEvent(eventId)
      .then(setEvent)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [eventId]);

  if (loading) return <div className="loading-state"><div className="spinner" /><p>Loading event...</p></div>;
  if (error || !event) return (
    <div className="error-state">
      <p>{error || 'Event not found'}</p>
      <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={() => navigate('/events')}>Back to Events</button>
    </div>
  );

  const components = event.impact?.components || {};
  const chartData = Object.entries(components).map(([key, value]) => ({
    name: key.replace(/_/g, ' '),
    value: value as number,
  }));

  return (
    <>
      <button className="btn btn-secondary btn-sm" onClick={() => navigate('/events')} style={{ marginBottom: '1rem' }}>
        <ArrowLeft size={16} /> Back to Events
      </button>

      <div className="page-header">
        <div>
          <h1>Event Detail</h1>
          <div className="page-header-sub">Signal ID: {event.signal_id}</div>
        </div>
        <span className={`risk-badge ${(event.impact?.risk_level ?? 'low').toLowerCase()}`}>{event.impact?.risk_level ?? 'LOW'}</span>
      </div>

      <div className="detail-grid">
        {/* Main content */}
        <div>
          {/* Original text */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header"><span className="card-title">Original Text</span></div>
            <div className="card-body">
              <p style={{ lineHeight: 1.7, color: 'var(--text-secondary)' }}>{event.text}</p>
              {event.source?.url && (
                <a href={event.source.url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--accent-blue)' }}>
                  Open Original Source <ExternalLink size={14} />
                </a>
              )}
            </div>
          </div>

          {/* Impact explainability */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header"><span className="card-title">Why this score? — Impact Breakdown</span></div>
            <div className="card-body">
              {chartData.length > 0 ? (
                <>
                  <div className="chart-container" style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis type="number" domain={[0, 'auto']} tick={{ fontSize: 11 }} />
                        <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Bar dataKey="value" fill="#2563eb" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ marginTop: '0.75rem' }}>
                    {chartData.map(d => (
                      <div key={d.name} className="impact-bar">
                        <span className="impact-bar-label">{d.name}</span>
                        <div className="impact-bar-track">
                          <div className="impact-bar-fill" style={{ width: `${Math.min(100, (d.value / 2) * 100)}%`, background: d.value > 1.5 ? 'var(--risk-high)' : 'var(--accent-blue)' }} />
                        </div>
                        <span className="impact-bar-value">{d.value.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p style={{ color: 'var(--text-tertiary)' }}>No component breakdown available</p>
              )}
            </div>
          </div>

          {/* Explanation */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header"><span className="card-title">Explanation</span></div>
            <div className="card-body">
              {(event.explanation || []).map((line: string, i: number) => (
                <div key={i} style={{ padding: '0.4rem 0', fontSize: '0.85rem', color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-light)' }}>{line}</div>
              ))}
            </div>
          </div>

          {/* Related events */}
          {event.related_events?.length > 0 && (
            <div className="card">
              <div className="card-header"><span className="card-title">Related Events (Same Cluster)</span></div>
              <div className="card-body">
                {event.related_events.map((r: any, i: number) => (
                  <div key={r.signal_id || i} className="event-card" style={{ marginBottom: '0.5rem' }} onClick={() => navigate(`/events/${r.signal_id}`)}>
                    <div className="event-card-text">{r.text?.slice(0, 120)}...</div>
                    <div className="event-card-tags">
                      <span className="tag">Impact: {r.impact?.score}</span>
                      <span className={`risk-badge ${(r.impact?.risk_level ?? 'low').toLowerCase()}`}>{r.impact?.risk_level}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div>
          {/* Risk info */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header"><span className="card-title">Risk Summary</span></div>
            <div className="card-body">
              <DetailRow label="Impact Score" value={`${event.impact?.score ?? 0} / 10`} />
              <DetailRow label="Risk Level" value={event.impact?.risk_level ?? '—'} />
              <DetailRow label="Trajectory" value={event.risk_trajectory ?? '—'} />
              <DetailRow label="Overall Confidence" value={(event.confidence_score ?? 0).toFixed(3)} />
              <DetailRow label="Novelty" value={(event.novelty_score ?? 0).toFixed(3)} />
              <DetailRow label="Corroboration" value={(event.corroboration_score ?? event.corroboration?.score ?? 0).toFixed(3)} />
              <DetailRow label="Source Credibility" value={(event.source_credibility ?? 0).toFixed(2)} />
              <DetailRow label="Processing Time" value={`${event.processing_time_ms ?? 0}ms`} />
            </div>
          </div>

          {/* Sentiment */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header"><span className="card-title">Sentiment</span></div>
            <div className="card-body">
              <DetailRow label="Label" value={event.sentiment?.label ?? '—'} />
              <DetailRow label="Score" value={event.sentiment?.score?.toFixed(4) ?? '—'} />
              <DetailRow label="Confidence" value={event.sentiment?.confidence?.toFixed(4) ?? '—'} />
              <DetailRow label="Model" value={event.sentiment?.model ?? '—'} />
            </div>
          </div>

          {/* Event Classification */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header"><span className="card-title">Event Classification</span></div>
            <div className="card-body">
              <DetailRow label="Class" value={event.event?.class ?? '—'} />
              <DetailRow label="Confidence" value={(event.event?.confidence ?? 0).toFixed(4)} />
              <DetailRow label="Model" value={event.event?.model ?? '—'} />
            </div>
          </div>

          {/* Entities */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header"><span className="card-title">Entities</span></div>
            <div className="card-body">
              {(event.entities || []).map((e: any, i: number) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid var(--border-light)', fontSize: '0.8rem', cursor: 'pointer' }}
                  onClick={() => navigate(`/entities/${encodeURIComponent(e.canonical_name || e.name)}`)}>
                  <span>{e.canonical_name || e.name} {e.ticker ? `(${e.ticker})` : ''}</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>{e.type} · {(e.confidence ?? 0).toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Source */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header"><span className="card-title">Source</span></div>
            <div className="card-body">
              <DetailRow label="Name" value={event.source?.name ?? '—'} />
              <DetailRow label="Type" value={event.source?.type ?? '—'} />
              <DetailRow label="Timestamp" value={event.timestamp ? new Date(event.timestamp).toLocaleString() : '—'} />
            </div>
          </div>

          {/* Stress results */}
          {event.stress_results?.length > 0 && (
            <div className="card">
              <div className="card-header"><span className="card-title">Stress Tests</span></div>
              <div className="card-body">
                {event.stress_results.map((s: any, i: number) => (
                  <div key={i} style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--border-light)' }}>
                    <div style={{ fontWeight: 500, fontSize: '0.85rem' }}>{s.scenario}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--risk-critical)' }}>Loss: {s.loss_percentage?.toFixed(1)}%</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function DetailRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="detail-row">
      <span className="detail-label">{label}</span>
      <span className="detail-value">{value}</span>
    </div>
  );
}
