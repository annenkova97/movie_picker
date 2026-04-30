/**
 * Unit tests for the LocalLibrary path. The Backend variant is exercised in
 * the Python integration tests (tests/test_auth_and_movies.py).
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ApiMovie } from './types';
import { getLibrary, syntheticId, LOCAL_LIBRARY_MAX_RECORDS, LocalLibraryFullError } from './library';

// Mock the API surface — LocalLibrary still calls /api/search and the
// preview endpoint for free-form add. Stub them so we don't hit the network.
vi.mock('./api', async () => {
  const actual = await vi.importActual<typeof import('./api')>('./api');
  return {
    ...actual,
    searchMovies: vi.fn(async (q: string) => [
      { imdb_id: 'tt0111161', title: 'The Shawshank Redemption', year: '1994', poster_url: null },
    ]),
    getMoviePreview: vi.fn(async (imdbId: string) => ({
      imdb_id: imdbId,
      title: 'Mock title',
      year: 2000,
      poster_url: null,
      imdb_rating: 8.5,
      genres: ['Drama'],
      plot: 'plot',
      director: 'dir',
      cast: [],
      awards: null,
    })),
    importFromInstagramParse: vi.fn(),
    importFromTelegramParse: vi.fn(),
    bulkImportMovies: vi.fn(),
    addMovie: vi.fn(),
    addMovieByImdbId: vi.fn(),
    importFromInstagram: vi.fn(),
    importFromTelegram: vi.fn(),
    listMovies: vi.fn(),
    patchMovie: vi.fn(),
    deleteMovie: vi.fn(),
    saveToLibrary: vi.fn(),
  };
});

const lib = getLibrary(true); // guest

beforeEach(() => {
  localStorage.clear();
});

describe('LocalLibrary', () => {
  it('starts empty', async () => {
    expect(await lib.list()).toEqual([]);
  });

  it('saves a movie by imdb_id and lists it back', async () => {
    const saved = await lib.saveByImdbId('tt0111161', false);
    expect(saved.imdb_id).toBe('tt0111161');

    const all = await lib.list();
    expect(all).toHaveLength(1);
    expect(all[0].in_library).toBe(true);
  });

  it('saving the same imdb_id twice is idempotent', async () => {
    await lib.saveByImdbId('tt0111161', false);
    await lib.saveByImdbId('tt0111161', false);

    const all = await lib.list();
    expect(all).toHaveLength(1);
  });

  it('saving the same imdb_id with watched=true updates the flag', async () => {
    await lib.saveByImdbId('tt0111161', false);
    const updated = await lib.saveByImdbId('tt0111161', true);
    expect(updated.is_watched).toBe(true);

    const all = await lib.list();
    expect(all).toHaveLength(1);
    expect(all[0].is_watched).toBe(true);
  });

  it('patch updates is_watched', async () => {
    const saved = await lib.saveByImdbId('tt0111161', false);
    await lib.patch(saved.id, { is_watched: true });

    const all = await lib.list();
    expect(all[0].is_watched).toBe(true);
  });

  it('remove drops the record', async () => {
    const saved = await lib.saveByImdbId('tt0111161', false);
    await lib.remove(saved.id);
    expect(await lib.list()).toEqual([]);
  });

  it('remove on missing id throws', async () => {
    await expect(lib.remove(999999)).rejects.toThrow();
  });

  it('absorbShared adds a snapshot, dedupes existing, marks rec_source=friends', async () => {
    // Pre-existing
    await lib.saveByImdbId('tt0111161', false);

    const incoming: ApiMovie[] = [
      // duplicate — should be skipped
      makeMovie('tt0111161', 'Existing'),
      // new — should be added
      makeMovie('tt0073195', 'Jaws'),
    ];

    const added = await lib.absorbShared(incoming);
    expect(added).toHaveLength(1);
    expect(added[0].imdb_id).toBe('tt0073195');
    expect(added[0].rec_source).toBe('friends');
    expect(added[0].source).toBe('friends');

    const all = await lib.list();
    expect(all).toHaveLength(2);
  });

  it('absorbShared on empty input is a no-op', async () => {
    const added = await lib.absorbShared([]);
    expect(added).toEqual([]);
  });

  it('saveByImdbId throws LocalLibraryFullError near the soft cap', async () => {
    // Pre-fill localStorage with sentinel rows so the next save trips the cap.
    const seed: ApiMovie[] = Array.from({ length: LOCAL_LIBRARY_MAX_RECORDS }, (_, i) => makeMovie(`tt${1000000 + i}`));
    localStorage.setItem('lentochka.library.v1', JSON.stringify(seed));

    await expect(lib.saveByImdbId('tt9999999', false)).rejects.toBeInstanceOf(LocalLibraryFullError);
  });
});

describe('syntheticId', () => {
  it('is stable for the same imdb_id', () => {
    expect(syntheticId('tt0111161')).toBe(syntheticId('tt0111161'));
  });

  it('is positive 31-bit', () => {
    const id = syntheticId('tt0111161');
    expect(id).toBeGreaterThanOrEqual(0);
    expect(id).toBeLessThan(2 ** 31);
  });

  it('different inputs hash to different ids (most of the time)', () => {
    expect(syntheticId('tt0111161')).not.toBe(syntheticId('tt0073195'));
  });
});


function makeMovie(imdbId: string, title = 'X'): ApiMovie {
  return {
    id: 1,
    imdb_id: imdbId,
    title,
    original_title: null,
    year: 2000,
    genres: [],
    description: null,
    plot: null,
    plot_ru: null,
    cast: [],
    director: null,
    poster_url: null,
    imdb_rating: null,
    awards: null,
    is_watched: false,
    source: 'personal',
    rec_source: 'personal',
    rec_note: null,
    in_library: true,
    award: null,
    award_year: null,
    added_at: '2026-04-30T12:00:00',
  };
}
