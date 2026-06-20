import { describe, expect, it } from 'vitest';
import { streamingLabel } from './ProviderBadges';
import type { WatchAvailability } from '../api';

function av(...names: string[]): WatchAvailability {
  return {
    region: 'RU',
    link: null,
    flatrate: names.map((name, i) => ({ provider_id: i + 1, name, logo_url: null })),
    rent: [],
    buy: [],
  };
}

describe('streamingLabel', () => {
  it('returns undefined with no availability or no flatrate', () => {
    expect(streamingLabel(undefined)).toBeUndefined();
    expect(streamingLabel(null)).toBeUndefined();
    expect(streamingLabel(av())).toBeUndefined();
  });

  it('returns the single provider name', () => {
    expect(streamingLabel(av('Netflix'))).toBe('Netflix');
  });

  it('summarises multiple providers as "first +N"', () => {
    expect(streamingLabel(av('Netflix', 'Amazon'))).toBe('Netflix +1');
    expect(streamingLabel(av('Netflix', 'Amazon', 'Okko'))).toBe('Netflix +2');
  });
});
