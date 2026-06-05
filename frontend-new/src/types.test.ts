import { describe, it, expect } from 'vitest';
import { toUiMovie, type ApiMovie } from './types';

function apiMovie(overrides: Partial<ApiMovie> = {}): ApiMovie {
  return {
    id: 1, imdb_id: 'tt1', title: 'X', original_title: null, year: 2000,
    genres: [], description: null, plot: null, plot_ru: null, cast: [],
    director: null, poster_url: null, imdb_rating: 8, awards: null,
    is_watched: true, source: 'personal', added_at: '2026-01-01T00:00:00',
    ...overrides,
  };
}

describe('toUiMovie diary fields', () => {
  it('maps user_rating and user_note into camelCase UiMovie fields', () => {
    const ui = toUiMovie(apiMovie({ user_rating: 5, user_note: 'unforgettable' }));
    expect(ui.userRating).toBe(5);
    expect(ui.userNote).toBe('unforgettable');
  });

  it('defaults absent diary fields to null', () => {
    const ui = toUiMovie(apiMovie());
    expect(ui.userRating).toBeNull();
    expect(ui.userNote).toBeNull();
  });
});
