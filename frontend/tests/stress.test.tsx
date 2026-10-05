import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import StressTestingPage from '../src/pages/StressTesting';
import * as api from '../src/api/client';

vi.mock('../src/api/client');

describe('StressTestingPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders scenarios and runs stress test', async () => {
    vi.mocked(api.fetchStressScenarios).mockResolvedValue({
      scenarios: [
        { name: 'GEOPOLITICAL_SHOCK', description: 'Conflict shock' },
        { name: 'MACRO_RATE_SHOCK', description: 'Rate shock' },
      ],
    });
    vi.mocked(api.fetchStressResults).mockResolvedValue({
      results: [],
    });
    vi.mocked(api.runStressTest).mockResolvedValue({
      simulation_id: 'test-sim-1',
      scenario: 'GEOPOLITICAL_SHOCK',
      portfolio_before: 100000000,
      portfolio_after: 92000000,
      absolute_loss: 8000000,
      loss_percentage: 8.0,
      asset_level_impacts: [
        { asset_class: 'Equities', impact_pct: -10, before_value: 20000000, after_value: 18000000 },
      ],
    });

    render(<StressTestingPage />);

    await waitFor(() => {
      expect(screen.getByText('Stress Testing')).toBeDefined();
    });

    const runBtn = screen.getByRole('button', { name: /run stress test/i });
    expect(runBtn).toBeDefined();

    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(api.runStressTest).toHaveBeenCalledWith('GEOPOLITICAL_SHOCK');
    });
  });
});
