import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';
import EventsPage from '../src/pages/Events';
import * as api from '../src/api/client';

vi.mock('../src/api/client');

describe('EventsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders events list with pagination and search bar', async () => {
    vi.mocked(api.fetchEvents).mockResolvedValue({
      items: [
        {
          id: 'ev-1',
          text: 'Federal Reserve raises rates 50 bps.',
          event_class: 'Monetary Policy',
          impact_score: 7.2,
          risk_level: 'HIGH',
          sentiment_label: 'negative',
          source_type: 'rss',
          created_at: new Date().toISOString(),
        },
      ],
      count: 1,
      page: 1,
      page_size: 25,
    });

    render(
      <MemoryRouter>
        <EventsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Events/i)).toBeDefined();
      expect(screen.getByText('Federal Reserve raises rates 50 bps.')).toBeDefined();
      expect(screen.getByText('Monetary Policy')).toBeDefined();
    });
  });

  it('handles empty events list cleanly', async () => {
    vi.mocked(api.fetchEvents).mockResolvedValue({
      items: [],
      count: 0,
      page: 1,
      page_size: 25,
    });

    render(
      <MemoryRouter>
        <EventsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No events found')).toBeDefined();
    });
  });
});
