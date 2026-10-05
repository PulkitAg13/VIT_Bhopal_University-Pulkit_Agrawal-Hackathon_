import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';
import DashboardPage from '../src/pages/Dashboard';
import * as api from '../src/api/client';

vi.mock('../src/api/client');

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders overview metrics and portfolio summary', async () => {
    vi.mocked(api.fetchRiskOverview).mockResolvedValue({
      overall_risk: 'MODERATE',
      active_events: 12,
      critical_signals: 2,
      average_impact: 5.4,
    });
    vi.mocked(api.fetchRiskTimeline).mockResolvedValue([
      { date: '2026-10-01', impact: 4.5 },
      { date: '2026-10-02', impact: 6.2 },
    ]);
    vi.mocked(api.fetchEvents).mockResolvedValue({
      items: [
        {
          id: 'ev-test-1',
          text: 'Central bank unexpected policy announcement.',
          event_class: 'Monetary Policy',
          impact_score: 6.5,
          risk_level: 'MODERATE',
          sentiment_label: 'neutral',
        },
      ],
      count: 1,
      page: 1,
      page_size: 5,
    });
    vi.mocked(api.fetchPortfolioExposure).mockResolvedValue({
      total_portfolio_value: 100000000,
      total_exposed_value: 25000000,
      exposure_percentage: 0.25,
    });
    vi.mocked(api.fetchHealth).mockResolvedValue({
      status: 'ok',
      database: 'connected',
      redis: 'connected',
    });
    vi.mocked(api.createWebSocket).mockReturnValue({
      close: vi.fn(),
    } as any);

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Risk Intelligence Dashboard')).toBeDefined();
      expect(screen.getByText('Central bank unexpected policy announcement.')).toBeDefined();
    });
  });
});
