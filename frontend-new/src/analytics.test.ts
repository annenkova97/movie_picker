/**
 * Unit tests for the analytics buffer. The single hard requirement: `track()`
 * must never throw and a failing send must never surface.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const sendEvents = vi.fn(async (_events: unknown[]) => {});

vi.mock('./api', () => ({
  sendEvents: (events: unknown[]) => sendEvents(events),
}));

import { track, flush } from './analytics';

beforeEach(() => {
  sendEvents.mockClear();
  sendEvents.mockResolvedValue(undefined);
  localStorage.clear();
  flush(); // drain any leftover buffer between tests
  sendEvents.mockClear();
});

describe('analytics', () => {
  it('buffers events and flushes them as one batch', () => {
    track('app_open', { a: 1 });
    track('share_opened');
    flush();

    expect(sendEvents).toHaveBeenCalledTimes(1);
    const batch = sendEvents.mock.calls[0][0] as Array<{ name: string; anon_id: string }>;
    expect(batch.map((e) => e.name)).toEqual(['app_open', 'share_opened']);
    expect(batch[0].anon_id).toBeTruthy();
  });

  it('does not send when the buffer is empty', () => {
    flush();
    expect(sendEvents).not.toHaveBeenCalled();
  });

  it('never throws even if sendEvents rejects', () => {
    sendEvents.mockRejectedValueOnce(new Error('network down'));
    expect(() => {
      track('app_open');
      flush();
    }).not.toThrow();
  });

  it('reuses a stable anon_id across flushes', () => {
    track('app_open');
    flush();
    track('app_open');
    flush();

    const first = (sendEvents.mock.calls[0][0] as Array<{ anon_id: string }>)[0].anon_id;
    const second = (sendEvents.mock.calls[1][0] as Array<{ anon_id: string }>)[0].anon_id;
    expect(first).toBe(second);
  });
});
