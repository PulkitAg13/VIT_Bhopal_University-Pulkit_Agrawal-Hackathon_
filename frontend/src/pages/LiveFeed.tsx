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

  const loadFeed = () => {
    setLoading(true);
    setError('');
    api.fetchEvents({ page_size: 50 })
      .then(r => setEvents(r.items || []))
      .catch((err) => setError(err.message || 'Failed to load live feed'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadFeed();
  }, []);

  useEffect(() => {
    const ws = api.createWebSocket(
      (data) => setEvents(prev => [data, ...prev].slice(0, 100)),
      setWsStatus,
    );
    return () => ws.close();
  }, []);

  const handleIngest = async () => {
    setIngesting(true);
    try {
      const result = await api.ingestData(ingestSource, ingestTicker, 5);
      if (result.signals) {
        setEvents(prev => [...result.signals, ...prev].slice(0, 100));
      }
    } catch (err) {
      console.error('Ingestion failed', err);
    } finally {
      setIngesting(false);
    }
  };

  const filtered = events.filter(evt => {
    if (search && !(evt.text || '').toLowerCase().includes(search.toLowerCase())) return false;
    if (classFilter && evt.event?.class !== classFilter) return false;
    if (riskFilter && evt.impact?.risk_level !== riskFilter) return false;
    if (sentimentFilter && evt.sentiment?.label !== sentimentFilter) return false;
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
            <div key={evt.signal_id || i} className="event-card" onClick={() => evt.signal_id && navigate(`/events/${evt.signal_id}`)}>
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
