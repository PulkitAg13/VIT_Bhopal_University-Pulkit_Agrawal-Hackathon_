import { describe, it, expect, vi } from 'vitest';
import { createWebSocket } from '../src/api/client';

describe('WebSocket Client', () => {
  it('instantiates WebSocket and attaches event handlers', () => {
    const mockWs = {
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
      send: vi.fn(),
      close: vi.fn(),
    };

    const originalWebSocket = global.WebSocket;
    (global as any).WebSocket = vi.fn().mockImplementation(() => mockWs);

    const onMessage = vi.fn();
    const onStatus = vi.fn();

    const ws = createWebSocket(onMessage, onStatus);
    expect(global.WebSocket).toHaveBeenCalled();

    // Trigger onopen
    if (mockWs.onopen) (mockWs.onopen as any)();
    expect(onStatus).toHaveBeenCalledWith('LIVE');

    // Trigger onmessage
    const eventPayload = { signal_id: 'sig-1', text: 'Fed rate hike' };
    if (mockWs.onmessage) (mockWs.onmessage as any)({ data: JSON.stringify(eventPayload) });
    expect(onMessage).toHaveBeenCalledWith(eventPayload);

    // Trigger onclose
    if (mockWs.onclose) (mockWs.onclose as any)();
    expect(onStatus).toHaveBeenCalledWith('Disconnected');

    global.WebSocket = originalWebSocket;
  });
});
