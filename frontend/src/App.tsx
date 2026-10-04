import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, AlertTriangle, BellRing, Briefcase, CheckCircle2, Gauge, Globe, ShieldAlert, TrendingUp } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

type EventItem = {
  event_id?: string;
  source?: { name?: string; type?: string };
  text?: string;
  impact?: { score?: number; risk_level?: string };
  sentiment?: { score?: number; label?: string };
  event?: { class?: string; confidence?: number };
  confidence_score?: number;
  novelty_score?: number;
  corroboration_score?: number;
  risk_trajectory?: string;
};

type EventsResponse = {
  items?: EventItem[];
};

export default function App() {
  const [metrics, setMetrics] = useState<any>(null);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [liveStatus, setLiveStatus] = useState<string>('Monitoring');

  useEffect(() => {
    const load = async () => {
      try {
        const [metricsData, portfolioData, eventsData] = await Promise.all([
          fetchJson('/api/v1/metrics'),
          fetchJson('/api/v1/portfolio'),
          fetchJson<EventsResponse>('/api/v1/events'),
        ]);
        setMetrics(metricsData);
        setPortfolio(portfolioData);
        setEvents((eventsData.items ?? []).slice(0, 5));
      } catch (error) {
        console.error('Failed to fetch dashboard data', error);
      }
    };
    load();
  }, []);

  useEffect(() => {
    const socketUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws/risk-events`;
    const socket = new WebSocket(socketUrl);
    socket.onopen = () => setLiveStatus('LIVE');
    socket.onmessage = (event) => {
      try {
        const item = JSON.parse(event.data) as EventItem;
        setEvents((current) => [item, ...current].slice(0, 5));
      } catch (error) {
        console.error('Invalid websocket payload', error);
      }
    };
    socket.onclose = () => setLiveStatus('Fallback');
    return () => socket.close();
  }, []);

  const riskTimeline = useMemo(
    () => [
      { time: '09:00', risk: 4.1 },
      { time: '10:00', risk: 5.2 },
      { time: '11:00', risk: 6.8 },
      { time: '12:00', risk: 8.3 },
      { time: '13:00', risk: 8.9 },
      { time: '14:00', risk: 9.1 },
    ],
    [],
  );

  const alert = events[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="flex items-center gap-3 border-b border-slate-800 px-6 py-5">
          <div className="rounded-lg bg-cyan-500/10 p-2 text-cyan-400">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm uppercase tracking-[0.2em] text-slate-400">FinRisk</div>
            <div className="font-semibold text-white">Intelligence</div>
          </div>
        </div>
        <nav className="space-y-2 px-4 py-6 text-sm text-slate-300">
          <div className="rounded-lg bg-slate-800 px-3 py-2 font-medium text-white">Dashboard</div>
          <div className="rounded-lg px-3 py-2 hover:bg-slate-800">Live Feed</div>
          <div className="rounded-lg px-3 py-2 hover:bg-slate-800">Events</div>
          <div className="rounded-lg px-3 py-2 hover:bg-slate-800">Entities</div>
          <div className="rounded-lg px-3 py-2 hover:bg-slate-800">Portfolio</div>
          <div className="rounded-lg px-3 py-2 hover:bg-slate-800">Stress Testing</div>
          <div className="rounded-lg px-3 py-2 hover:bg-slate-800">Analytics</div>
        </nav>
      </aside>

      <main className="ml-64 p-8">
        <header className="mb-6 flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="text-xs uppercase tracking-[0.28em] text-slate-400">Risk Command Center</div>
            <h1 className="mt-2 text-3xl font-semibold text-white">Real-Time AI-Powered Financial Risk Intelligence</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              {liveStatus}
            </div>
            <button className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-100">Run Demo</button>
          </div>
        </header>

        <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {[
            { label: 'Overall market risk', value: '8.7 / 10', icon: Gauge },
            { label: 'Active high-risk events', value: metrics?.high_risk_events ?? '3', icon: AlertTriangle },
            { label: 'Critical events', value: metrics?.critical_events ?? '1', icon: BellRing },
            { label: 'Average sentiment', value: `${(metrics?.average_sentiment ?? -0.6).toFixed(2)}`, icon: TrendingUp },
            { label: 'Events processed', value: `${metrics?.events_processed ?? 14}`, icon: Activity },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
              <div className="mb-4 flex items-center justify-between text-slate-400">
                <span className="text-sm">{label}</span>
                <Icon className="h-4 w-4" />
              </div>
              <div className="text-2xl font-semibold text-white">{value}</div>
            </div>
          ))}
        </section>

        <section className="mb-6 grid gap-6 xl:grid-cols-[1.7fr_0.9fr]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Risk trajectory</div>
                <h2 className="mt-2 text-xl font-semibold text-white">Portfolio risk signal</h2>
              </div>
              <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs text-red-300">ACCELERATING</span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={riskTimeline}>
                  <defs>
                    <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.7} />
                      <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.1} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                  <XAxis dataKey="time" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Area type="monotone" dataKey="risk" stroke="#38bdf8" fill="url(#riskFill)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-4 text-xs uppercase tracking-[0.2em] text-slate-500">Stress trigger</div>
            <div className="mb-3 flex items-center justify-between text-white">
              <span className="font-medium">Geopolitical Shock</span>
              <span className="rounded-full border border-orange-400/30 bg-orange-500/10 px-2 py-1 text-xs text-orange-300">Triggered</span>
            </div>
            <div className="space-y-3 text-sm text-slate-300">
              <div className="flex justify-between"><span>Portfolio before</span><strong className="text-white">$100.0M</strong></div>
              <div className="flex justify-between"><span>Portfolio after</span><strong className="text-white">$89.1M</strong></div>
              <div className="flex justify-between"><span>Absolute loss</span><strong className="text-red-300">-$10.9M</strong></div>
              <div className="flex justify-between"><span>Loss %</span><strong className="text-red-300">-10.9%</strong></div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Live feed</div>
                <h2 className="mt-2 text-xl font-semibold text-white">Incoming risk events</h2>
              </div>
              <div className="flex items-center gap-2 text-xs text-emerald-300">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                {liveStatus}
              </div>
            </div>
            <div className="space-y-3">
              {(events.length ? events : [
                { text: 'Escalating geopolitical tensions disrupt critical energy supply routes, raising concerns over global inflation and corporate input costs.', impact: { score: 8.7, risk_level: 'HIGH' }, sentiment: { score: -0.78, label: 'negative' }, event: { class: 'Geopolitical', confidence: 0.91 }, source: { name: 'Yahoo Finance RSS' } },
              ]).map((item, index) => (
                <div key={index} className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
                  <div className="mb-2 flex items-start justify-between gap-4">
                    <div>
                      <div className="text-xs uppercase tracking-[0.14em] text-slate-500">{item.source?.name ?? 'Yahoo Finance RSS'}</div>
                      <div className="mt-1 text-sm text-slate-200">{item.text}</div>
                    </div>
                    <div className="rounded-lg bg-red-500/10 px-2 py-1 text-xs font-medium text-red-300">{item.impact?.risk_level ?? 'HIGH'}</div>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-slate-300">
                    <span className="rounded-full bg-slate-800 px-2 py-1">Entity: Apple</span>
                    <span className="rounded-full bg-slate-800 px-2 py-1">Sentiment: {item.sentiment?.label ?? 'negative'}</span>
                    <span className="rounded-full bg-slate-800 px-2 py-1">Event: {item.event?.class ?? 'Geopolitical'}</span>
                    <span className="rounded-full bg-slate-800 px-2 py-1">Impact: {item.impact?.score ?? '8.7'}</span>
                    <span className="rounded-full bg-slate-800 px-2 py-1">Confidence: {(item.confidence_score ?? item.event?.confidence ?? 0.91).toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-4 text-xs uppercase tracking-[0.2em] text-slate-500">Alert</div>
            {alert ? (
              <div className="space-y-3 text-sm text-slate-200">
                <div className="flex items-center justify-between rounded-lg bg-slate-950 p-3">
                  <span className="text-slate-400">Event</span>
                  <span className="font-medium text-white">{alert.event?.class ?? 'Geopolitical'}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-slate-950 p-3">
                  <span className="text-slate-400">Impact</span>
                  <span className="font-medium text-red-300">{alert.impact?.score ?? '8.7'} / 10</span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-slate-950 p-3">
                  <span className="text-slate-400">Confidence</span>
                  <span className="font-medium text-emerald-300">{(alert.confidence_score ?? alert.event?.confidence ?? 0.91).toFixed(2)}</span>
                </div>
                <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-3 text-cyan-200">
                  Portfolio stress test triggered for {alert.event?.class ?? 'Geopolitical'} risk with elevated portfolio exposure.
                </div>
              </div>
            ) : (
              <div className="rounded-lg bg-slate-950 p-4 text-slate-400">No live events yet.</div>
            )}
          </div>
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Portfolio exposure</h3>
              <Briefcase className="h-4 w-4 text-cyan-300" />
            </div>
            <div className="space-y-3 text-sm text-slate-300">
              {(portfolio?.positions ?? [
                { asset_class: 'Corporate Loans', value: 30000000 },
                { asset_class: 'Equities', value: 20000000 },
                { asset_class: 'Corporate Bonds', value: 15000000 },
              ]).slice(0, 3).map((position: any) => (
                <div key={position.asset_class} className="flex items-center justify-between rounded-lg bg-slate-950 p-2">
                  <span>{position.asset_class}</span>
                  <span className="text-white">${(position.value / 1_000_000).toFixed(1)}M</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Source credibility</h3>
              <Globe className="h-4 w-4 text-cyan-300" />
            </div>
            <div className="space-y-3 text-sm text-slate-300">
              {[
                ['Official regulatory', '0.92'],
                ['Major newswire', '0.81'],
                ['Market intelligence', '0.74'],
              ].map(([label, score]) => (
                <div key={label} className="flex items-center justify-between rounded-lg bg-slate-950 p-2">
                  <span>{label}</span>
                  <span className="text-white">{score}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Model status</h3>
              <CheckCircle2 className="h-4 w-4 text-emerald-300" />
            </div>
            <div className="space-y-3 text-sm text-slate-300">
              <div className="rounded-lg bg-slate-950 p-2">NLP pipeline: online</div>
              <div className="rounded-lg bg-slate-950 p-2">Entity resolution: active</div>
              <div className="rounded-lg bg-slate-950 p-2">Stress engine: ready</div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
