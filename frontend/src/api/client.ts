/**
 * API Client — Centralized HTTP client for all backend calls.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Health ────────────────────────────────────────
export const fetchHealth = () => request<any>('/api/v1/health');

// ── Risk Overview ────────────────────────────────
export const fetchRiskOverview = () => request<any>('/api/v1/risk/overview');
export const fetchRiskTimeline = () => request<any[]>('/api/v1/risk/timeline');

// ── Events ───────────────────────────────────────
export interface EventsParams {
  page?: number; page_size?: number; event_class?: string;
  risk_level?: string; source_type?: string; source?: string; sentiment?: string; search?: string;
}
export const fetchEvents = (params: EventsParams = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null && v !== '') qs.set(k, String(v)); });
  return request<{ items: any[]; count: number; page: number; page_size: number }>(
    `/api/v1/events?${qs.toString()}`
  );
};
export const fetchEvent = (id: string) => request<any>(`/api/v1/events/${id}`);

// ── Entities ─────────────────────────────────────
export const fetchEntities = (search?: string) => {
  const qs = search ? `?search=${encodeURIComponent(search)}` : '';
  return request<{ items: any[]; count: number }>(`/api/v1/entities${qs}`);
};
export const fetchEntity = (id: string) => request<any>(`/api/v1/entities/${encodeURIComponent(id)}`);

// ── Portfolio ────────────────────────────────────
export const fetchPortfolio = () => request<any>('/api/v1/portfolio');
export const fetchPortfolioExposure = () => request<any>('/api/v1/portfolio/exposure');

// ── Stress Testing ───────────────────────────────
export const fetchStressScenarios = () => request<{ scenarios: any[] }>('/api/v1/stress-test/scenarios');
export const runStressTest = (scenario: string) =>
  request<any>('/api/v1/stress-test', { method: 'POST', body: JSON.stringify({ scenario }) });
export const fetchStressResults = () => request<{ results: any[] }>('/api/v1/stress-test/results');
export const fetchStressResult = (id: string) => request<any>(`/api/v1/stress-test/${id}`);

// ── Analytics ────────────────────────────────────
export const fetchAnalytics = () => request<any>('/api/v1/analytics/overview');
export const fetchMetrics = () => request<any>('/api/v1/metrics');

// ── Ingestion ────────────────────────────────────
export const ingestData = (source: string, ticker: string, maxItems: number = 5) =>
  request<any>('/api/v1/ingest', {
    method: 'POST',
    body: JSON.stringify({ source, ticker, max_items: maxItems }),
  });

// ── Analysis ─────────────────────────────────────
export const analyzeText = (text: string, sourceName?: string, sourceType?: string) =>
  request<any>('/api/v1/analyze', {
    method: 'POST',
    body: JSON.stringify({ text, source_name: sourceName || 'manual', source_type: sourceType || 'manual' }),
  });

// ── Demo ─────────────────────────────────────────
export const runDemo = () => request<any>('/api/v1/demo/run', { method: 'POST' });

// ── WebSocket ────────────────────────────────────
export function createWebSocket(onMessage: (data: any) => void, onStatus?: (s: string) => void) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = API_BASE ? new URL(API_BASE).host : window.location.host;
  const url = `${proto}://${host}/ws/risk-events`;
  const ws = new WebSocket(url);
  ws.onopen = () => onStatus?.('LIVE');
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  ws.onclose = () => onStatus?.('Disconnected');
  ws.onerror = () => onStatus?.('Error');
  return ws;
}
