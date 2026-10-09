import { useEffect, useState } from 'react';
import { Settings, Send } from 'lucide-react';
import * as api from '../api/client';

export default function SettingsPage() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [analyzeText, setAnalyzeText] = useState('');
  const [analyzeResult, setAnalyzeResult] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const loadHealth = () => {
    setLoading(true);
    setError('');
    api.fetchHealth()
      .then(setHealth)
      .catch((err) => setError(err.message || 'Unable to reach backend'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadHealth();
  }, []);

  const handleAnalyze = async () => {
    if (!analyzeText.trim()) return;
    setAnalyzing(true);
    setAnalyzeResult(null);
    try {
      const result = await api.analyzeText(analyzeText);
      setAnalyzeResult(result);
    } catch (err: any) {
      setAnalyzeResult({ error: err.message });
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <>
      <div className="page-header"><h1>Settings & Tools</h1></div>

      {/* Manual Analysis */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header"><span className="card-title">Manual Text Analysis</span></div>
        <div className="card-body">
          <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginBottom: '0.75rem' }}>
            Enter financial text to run through the full NLP + risk pipeline.
          </p>
          <textarea
            className="input"
            rows={4}
            style={{ width: '100%', resize: 'vertical' }}
            placeholder="Enter financial text to analyze..."
            value={analyzeText}
            onChange={e => setAnalyzeText(e.target.value)}
          />
          <button className="btn btn-primary" onClick={handleAnalyze} disabled={analyzing || !analyzeText.trim()} style={{ marginTop: '0.75rem' }} id="analyze-btn">
            <Send size={16} /> {analyzing ? 'Analyzing...' : 'Analyze'}
          </button>

          {analyzeResult && !analyzeResult.error && (
            <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-tertiary)', borderRadius: 8 }}>
              <div className="kpi-grid" style={{ marginBottom: '1rem' }}>
                <div className="kpi-card">
                  <div className="kpi-label">Sentiment</div>
                  <div className="kpi-value" style={{ fontSize: '1.2rem', color: analyzeResult.sentiment?.label === 'negative' ? 'var(--sentiment-negative)' : analyzeResult.sentiment?.label === 'positive' ? 'var(--sentiment-positive)' : 'inherit' }}>
                    {analyzeResult.sentiment?.label} ({analyzeResult.sentiment?.score?.toFixed(3)})
                  </div>
                  <div className="kpi-sub">via {analyzeResult.sentiment?.model}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Event Class</div>
                  <div className="kpi-value" style={{ fontSize: '1.2rem' }}>{analyzeResult.event?.class}</div>
                  <div className="kpi-sub">Confidence: {analyzeResult.event?.confidence?.toFixed(3)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Impact</div>
                  <div className="kpi-value" style={{ fontSize: '1.2rem' }}>{analyzeResult.impact?.score}/10</div>
                  <div className="kpi-sub">{analyzeResult.impact?.risk_level}</div>
                </div>
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <strong>Entities:</strong> {(analyzeResult.entities || []).map((e: any) => `${e.canonical_name}${e.ticker ? ` (${e.ticker})` : ''}`).join(', ') || 'None'}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                <strong>Explanation:</strong>
                {(analyzeResult.explanation || []).map((line: string, i: number) => <div key={i} style={{ paddingLeft: '1rem' }}>• {line}</div>)}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '0.5rem' }}>
                Processing time: {analyzeResult.processing_time_ms}ms | Signal ID: {analyzeResult.signal_id}
              </div>
            </div>
          )}
          {analyzeResult?.error && (
            <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'var(--risk-critical-bg)', borderRadius: 8, color: 'var(--risk-critical)', fontSize: '0.85rem' }}>
              Error: {analyzeResult.error}
            </div>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header"><span className="card-title">System Status</span></div>
        <div className="card-body">
          {loading ? (
            <div className="loading-state"><div className="spinner" /></div>
          ) : error || !health ? (
            <div className="error-state">
              <p>{error || 'Unable to reach backend'}</p>
              <button className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }} onClick={loadHealth}>Retry</button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {[
                { label: 'Service', value: health.service || 'FinRisk Intelligence' },
                { label: 'Database', value: health.database },
                { label: 'Redis', value: health.redis },
                { label: 'FinBERT Model', value: health.models?.finbert },
                { label: 'Embedding Model', value: health.models?.embedding_model },
                { label: 'Event Classifier', value: health.models?.event_classifier },
                { label: 'Device', value: health.models?.device },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0.75rem', background: 'var(--bg-tertiary)', borderRadius: 6, fontSize: '0.85rem' }}>
                  <span>{label}</span>
                  <span style={{
                    fontWeight: 500,
                    color: value === 'ready' || value === 'connected' ? 'var(--risk-low)' :
                           value?.toString().startsWith('error') ? 'var(--risk-critical)' : 'var(--text-secondary)'
                  }}>{value ?? 'unknown'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* About */}
      <div className="card">
        <div className="card-header"><span className="card-title">About</span></div>
        <div className="card-body" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          <p><strong>FinRisk Intelligence v2.0</strong></p>
          <p style={{ marginTop: '0.5rem' }}>AI-powered financial risk intelligence platform for wholesale banking.</p>
          <p style={{ marginTop: '0.5rem' }}>
            Models: ProsusAI/finbert (sentiment), all-MiniLM-L6-v2 (embeddings), facebook/bart-large-mnli (classification)
          </p>
          <p style={{ marginTop: '0.5rem' }}>
            Data: Yahoo Finance RSS, Twitter Financial News datasets, Financial PhraseBank
          </p>
          <p style={{ marginTop: '0.5rem', color: 'var(--text-tertiary)', fontSize: '0.75rem' }}>
            Built for S & P Global Hackathon 2026 by Pulkit Agrawal.
          </p>
        </div>
      </div>
    </>
  );
}
