import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../src/api/client';

describe('API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchHealth calls /api/v1/health', async () => {
    const mockHealth = { status: 'ok', database: 'connected', redis: 'connected' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHealth),
    });

    const res = await api.fetchHealth();
    expect(res.status).toBe('ok');
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/health', expect.any(Object));
  });

  it('fetchEvents builds correct query string parameters', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [], count: 0, page: 1, page_size: 10 }),
    });

    await api.fetchEvents({ page: 2, risk_level: 'HIGH', event_class: 'Credit Event' });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('page=2'),
      expect.any(Object)
    );
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('risk_level=HIGH'),
      expect.any(Object)
    );
  });

  it('runStressTest posts scenario payload', async () => {
    const mockResult = { simulation_id: 'sim-123', loss_percentage: 8.5 };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResult),
    });

    const res = await api.runStressTest('GEOPOLITICAL_SHOCK');
    expect(res.simulation_id).toBe('sim-123');
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/stress-test', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ scenario: 'GEOPOLITICAL_SHOCK' }),
    }));
  });

  it('handles API error status gracefully', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve('Resource not found'),
    });

    await expect(api.fetchEvent('unknown-id')).rejects.toThrow('404 Not Found');
  });
});
