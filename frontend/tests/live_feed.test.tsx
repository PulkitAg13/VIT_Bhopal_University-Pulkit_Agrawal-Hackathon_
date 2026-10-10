import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';
import LiveFeedPage from '../src/pages/LiveFeed';
import * as api from '../src/api/client';

vi.mock('../src/api/client');

describe('LiveFeedPage Synchronization', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (api.createWebSocket as any).mockReturnValue({ close: vi.fn() });
  });

  it('keeps newly ingested events immediately visible after Fetch & Analyze completes', async () => {
    const initialEvents = [
      {
        signal_id: 'sig-old-1',
        text: 'Old initial event',
        source: { name: 'RSS' },
        impact: { risk_level: 'LOW', score: 1 },
        event: { class: 'Market Movement', confidence: 0.9 },
        sentiment: { label: 'neutral', score: 0.1 },
        timestamp: new Date().toISOString(),
      },
    ];

    const newlyIngestedSignals = [
      {
        signal_id: 'sig-new-1',
        text: 'Newly ingested Twitter event',
        source: { name: 'Dataset Replay (twitter_sentiment)' },
        impact: { risk_level: 'HIGH', score: 8 },
        event: { class: 'Credit Event', confidence: 0.95 },
        sentiment: { label: 'negative', score: -0.8 },
        timestamp: new Date().toISOString(),
      },
    ];

    // Initial fetch returns old event
    vi.mocked(api.fetchEvents).mockResolvedValueOnce({
      items: initialEvents,
      count: 1,
      page: 1,
      page_size: 50,
    });

    // Ingest returns new event
    vi.mocked(api.ingestData).mockResolvedValueOnce({
      ingested: 1,
      source: 'dataset',
      signals: newlyIngestedSignals,
    });

    // Refetch after ingest returns updated list with new event first
    vi.mocked(api.fetchEvents).mockResolvedValueOnce({
      items: [...newlyIngestedSignals, ...initialEvents],
      count: 2,
      page: 1,
      page_size: 50,
    });

    render(
      <MemoryRouter>
        <LiveFeedPage />
      </MemoryRouter>
    );

    // Initial event renders
    await waitFor(() => {
      expect(screen.getByText('Old initial event')).toBeDefined();
    });

    // Click ingest
    const ingestBtn = screen.getByRole('button', { name: /Fetch & Analyze/i });
    fireEvent.click(ingestBtn);

    // Newly ingested event must remain visible
    await waitFor(() => {
      expect(screen.getByText('Newly ingested Twitter event')).toBeDefined();
      expect(screen.getByText('Old initial event')).toBeDefined();
    });

    expect(api.ingestData).toHaveBeenCalled();
    expect(api.fetchEvents).toHaveBeenCalledTimes(2);
  });

  it('prevents stale in-flight events query from overwriting WebSocket updates', async () => {
    let wsCallback: any = null;
    vi.mocked(api.createWebSocket).mockImplementation((onMsg: any, onStatus: any) => {
      wsCallback = onMsg;
      onStatus?.('LIVE');
      return { close: vi.fn() } as any;
    });

    let resolveInitialFetch: any = null;
    const initialFetchPromise = new Promise((resolve) => {
      resolveInitialFetch = resolve;
    });

    vi.mocked(api.fetchEvents).mockImplementation(() => initialFetchPromise as any);

    render(
      <MemoryRouter>
        <LiveFeedPage />
      </MemoryRouter>
    );

    // Simulate WebSocket event arriving before initial fetch resolves
    act(() => {
      wsCallback({
        signal_id: 'ws-event-1',
        text: 'Live breaking event over WebSocket',
        event_class: 'Geopolitical',
        risk_level: 'CRITICAL',
        timestamp: new Date().toISOString(),
      });
    });

    // Now resolve the older initial fetch with old event
    await act(async () => {
      resolveInitialFetch({
        items: [
          {
            signal_id: 'sig-old-1',
            text: 'Stale query event',
            source: { name: 'RSS' },
            timestamp: new Date().toISOString(),
          },
        ],
        count: 1,
        page: 1,
        page_size: 50,
      });
    });

    // The WebSocket event must NOT have been overwritten by stale query items
    await waitFor(() => {
      expect(screen.getByText('Live breaking event over WebSocket')).toBeDefined();
      expect(screen.getByText('Stale query event')).toBeDefined();
    });
  });
});
