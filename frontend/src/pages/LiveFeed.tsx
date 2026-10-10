import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Radio, Search } from 'lucide-react';
import * as api from '../api/client';

export default function LiveFeedPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [wsStatus, setWsStatus] = useState('Connecting...');
  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [ingestSource, setIngestSource] = useState('rss');
  const [ingestTicker, setIngestTicker] = useState('AAPL');

  const normalizeEvent = (evt: any) => ({
    ...evt,
    signal_id: evt.signal_id || evt.id || evt.event_id,
    event: evt.event || (evt.event_class ? { class: evt.event_class, confidence: evt.event_confidence ?? 1.0 } : undefined),
    impact: evt.impact || (evt.risk_level ? { risk_level: evt.risk_level, score: evt.impact_score ?? 0 } : undefined),
    sentiment: evt.sentiment || (evt.sentiment_label ? { label: evt.sentiment_label, score: evt.sentiment_score ?? 0 } : undefined),
  });

  const loadFeed = async (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
      setError('');
    }
    try {
      const r = await api.fetchEvents({ page_size: 50 });
      if (r.items) {
        setEvents(prev => {
          const serverItems = r.items.map(normalizeEvent);
          const serverIds = new Set(serverItems.map((e: any) => e.signal_id).filter(Boolean));
          // Preserve any newly received events (e.g. from WebSocket) that aren't yet in server batch
          const newerWsEvents = prev.filter(e => {
            const id = e.signal_id || e.id;
            return id && !serverIds.has(id);
          });
          return [...newerWsEvents, ...serverItems].slice(0, 100);
        });
      }
    } catch (err: any) {
      if (showLoading) {
        setError(err.message || 'Failed to load live feed');
      } else {
        console.error('Failed to refresh feed', err);
      }
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    loadFeed(true);
  }, []);

  useEffect(() => {
    const ws = api.createWebSocket(
      (data) => {
        setEvents(prev => {
          const norm = normalizeEvent(data);
          const id = norm.signal_id;
          if (id && prev.some(e => (e.signal_id || e.id) === id)) {
            return prev;
          }
          return [norm, ...prev].slice(0, 100);
        });
      },
      setWsStatus,
    );
    return () => ws.close();
  }, []);

  const handleIngest = async () => {
    setIngesting(true);
    try {
      const result = await api.ingestData(ingestSource, ingestTicker, 5);
      if (result.signals && result.signals.length > 0) {
        setEvents(prev => {
          const newSignals = result.signals.map(normalizeEvent);
          const existingIds = new Set(prev.map((e: any) => e.signal_id || e.id).filter(Boolean));
          const uniqueNew = newSignals.filter((s: any) => !existingIds.has(s.signal_id || s.id));
          return [...uniqueNew, ...prev].slice(0, 100);
        });
      }
      await loadFeed(false);
    } catch (err) {
      console.error('Ingestion failed', err);
    } finally {
      setIngesting(false);
    }
  };

  const filtered = events.filter(evt => {
    if (search && !(evt.text || '').toLowerCase().includes(search.toLowerCase())) return false;
    const evtClass = evt.event?.class || evt.event_class;
    if (classFilter && evtClass !== classFilter) return false;
    const evtRisk = evt.impact?.risk_level || evt.risk_level;
    if (riskFilter && evtRisk !== riskFilter) return false;
    const evtSent = evt.sentiment?.label || evt.sentiment_label;
    if (sentimentFilter && evtSent !== sentimentFilter) return false;
    return true;
  });

  if (loading) return <div className="loading-state"><div className="spinner" /><p>Loading live feed...</p></div>;
  if (error) return (
    <div className="error-state">
      <AlertTriangle size={48} style={{ color: 'var(--risk-critical)' }} />
      <p>{error}</p>
      <button className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }} onClick={loadFeed}>Retry</button>
    </div>
  );

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Live Feed</h1>
          <div className="page-header-sub">Real-time incoming risk events</div>
        </div>
        <span className={`risk-badge ${wsStatus === 'LIVE' ? 'low' : 'moderate'}`}>● {wsStatus}</span>
      </div>

      {/* Ingestion Control */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="card-header">
          <span className="card-title">Fetch & Ingest Data</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
            Supports Live RSS, Historical Datasets & Synthetic Scenarios
          </span>
        </div>
        <div className="card-body">
          <div className="filter-bar">
            <select className="select" value={ingestSource} onChange={e => setIngestSource(e.target.value)}>
              <option value="rss">Yahoo Finance RSS (Live News)</option>
              <option value="dataset">Dataset Replay (Twitter Financial News)</option>
              <option value="demo">Synthetic Demo Scenario</option>
            </select>
            <select className="select" value={ingestTicker} onChange={e => setIngestTicker(e.target.value)}>
              {['AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','JPM','BAC','XOM'].map(t =>
                <option key={t} value={t}>{t}</option>
              )}
            </select>
            <button className="btn btn-primary" onClick={handleIngest} disabled={ingesting} id="ingest-btn">
              {ingesting ? 'Processing Pipeline...' : 'Fetch & Analyze'}
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)' }} />
          <input className="input" style={{ paddingLeft: 32, width: '100%' }} placeholder="Search events..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="select" value={classFilter} onChange={e => setClassFilter(e.target.value)}>
          <option value="">All Classes</option>
          {['Geopolitical','Macroeconomic','Credit Event','Earnings','Regulatory / Legal','Monetary Policy','Commodity / Energy','Market Movement','Liquidity','Supply Chain'].map(c =>
            <option key={c} value={c}>{c}</option>
          )}
        </select>
        <select className="select" value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
          <option value="">All Risk Levels</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MODERATE">Moderate</option>
          <option value="LOW">Low</option>
        </select>
        <select className="select" value={sentimentFilter} onChange={e => setSentimentFilter(e.target.value)}>
          <option value="">All Sentiment</option>
          <option value="positive">Positive</option>
          <option value="negative">Negative</option>
          <option value="neutral">Neutral</option>
        </select>
      </div>

      {/* Events */}
      {filtered.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {filtered.map((evt, i) => (
            <div key={evt.signal_id || evt.id || i} className="event-card" onClick={() => (evt.signal_id || evt.id) && navigate(`/events/${evt.signal_id || evt.id}`)}>
              <div className="event-card-header">
                <div>
                  <div className="event-card-source">{evt.source?.name ?? 'Unknown'}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>{evt.timestamp ? new Date(evt.timestamp).toLocaleString() : ''}</div>
                </div>
                <span className={`risk-badge ${(evt.impact?.risk_level ?? 'low').toLowerCase()}`}>
                  {evt.impact?.risk_level ?? 'LOW'}
                </span>
              </div>
              <div className="event-card-text">{evt.text}</div>
              <div className="event-card-tags">
                <span className="tag">Impact: {evt.impact?.score ?? 0}</span>
                <span className="tag">{evt.event?.class ?? '—'}</span>
                <span className="tag">Sentiment: {evt.sentiment?.label ?? '—'} ({evt.sentiment?.score?.toFixed(2) ?? '0'})</span>
                <span className="tag">Confidence: {(evt.confidence_score ?? evt.event?.confidence ?? 0).toFixed(2)}</span>
                {evt.entities?.slice(0, 2).map((e: any, j: number) => <span key={j} className="tag">{e.canonical_name || e.name}</span>)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state" style={{ marginTop: '2rem' }}>
          <Radio size={48} />
          <p>No events match the current filters. Try fetching new data above.</p>
        </div>
      )}
    </>
  );
}
