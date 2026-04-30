/**
 * Movie library abstraction.
 *
 * Two implementations:
 *   - BackendLibrary: standard authenticated user — talks to /api/movies/*.
 *   - LocalLibrary: guest user — persists in localStorage, no auth.
 *
 * Components consume `useLibrary()` (see hooks/useLibrary.ts) and never
 * branch on auth state directly. Migration from local → backend happens
 * once on registration/login (see migrateGuestLibrary in auth.tsx).
 */

import type { ApiMovie } from './types';
import {
  addMovie as apiAddMovie,
  addMovieByImdbId,
  bulkImportMovies,
  deleteMovie as apiDeleteMovie,
  getMoviePreview,
  importFromInstagram as apiImportFromInstagram,
  importFromInstagramParse,
  listMovies as apiListMovies,
  patchMovie as apiPatchMovie,
  saveToLibrary as apiSaveToLibrary,
  searchMovies,
} from './api';

// ── Local storage ────────────────────────────────────────────────────────────

const LOCAL_STORAGE_KEY = 'lentochka.library.v1';

// Soft cap: localStorage allows ~5MB per origin. One ApiMovie ≈ 1–2KB JSON, so
// 2000 records is a comfortable ceiling that still leaves headroom for other
// keys (tokens, lang, theme, prompt-shown flags).
export const LOCAL_LIBRARY_MAX_RECORDS = 2000;

export class LocalLibraryFullError extends Error {
  constructor() {
    super('Local library is full. Sign up to keep saving.');
    this.name = 'LocalLibraryFullError';
  }
}

function readLocal(): ApiMovie[] {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeLocal(movies: ApiMovie[]): void {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(movies));
  } catch (e) {
    console.warn('[library] failed to persist local library', e);
  }
}

/**
 * Stable positive-int id derived from imdb_id. Used as synthetic primary key
 * for guest library so that React Query can identify movies and the recommend
 * endpoint can echo IDs back. Collisions with real backend ids are not a
 * concern because LocalLibrary and BackendLibrary are mutually exclusive at
 * runtime (one user is either guest OR signed in, never both).
 */
export function syntheticId(imdbId: string): number {
  let h = 5381;
  for (let i = 0; i < imdbId.length; i++) {
    h = ((h << 5) + h + imdbId.charCodeAt(i)) >>> 0;
  }
  // keep within 31-bit positive range
  return h & 0x7fffffff;
}

function nowIso(): string {
  return new Date().toISOString();
}

function previewToApiMovie(
  imdbId: string,
  preview: Awaited<ReturnType<typeof getMoviePreview>>,
  watched: boolean,
): ApiMovie {
  return {
    id: syntheticId(imdbId),
    imdb_id: imdbId,
    title: preview.title,
    original_title: null,
    year: preview.year,
    genres: preview.genres ?? [],
    description: null,
    plot: preview.plot,
    plot_ru: null,
    cast: preview.cast ?? [],
    director: preview.director,
    poster_url: preview.poster_url,
    imdb_rating: preview.imdb_rating,
    awards: preview.awards,
    is_watched: watched,
    source: 'personal',
    rec_source: 'personal',
    rec_note: null,
    in_library: true,
    award: null,
    award_year: null,
    added_at: nowIso(),
  };
}

// MovieBase from /api/instagram/parse — has all metadata except DB id/watched/added_at.
type ParsedMovieBase = Awaited<ReturnType<typeof importFromInstagramParse>>[number];

function parsedToApiMovie(base: ParsedMovieBase): ApiMovie {
  return {
    id: syntheticId(base.imdb_id),
    imdb_id: base.imdb_id,
    title: base.title,
    original_title: base.original_title ?? null,
    year: base.year ?? null,
    genres: base.genres ?? [],
    description: base.description ?? null,
    plot: base.plot ?? null,
    plot_ru: base.plot_ru ?? null,
    cast: base.cast ?? [],
    director: base.director ?? null,
    poster_url: base.poster_url ?? null,
    imdb_rating: base.imdb_rating ?? null,
    awards: base.awards ?? null,
    is_watched: false,
    source: 'instagram',
    rec_source: 'instagram',
    rec_note: null,
    in_library: true,
    award: null,
    award_year: null,
    added_at: nowIso(),
  };
}

// ── Public interface ─────────────────────────────────────────────────────────

export interface MovieLibrary {
  /** True for the local-storage-backed guest library. */
  readonly isGuest: boolean;
  list(): Promise<ApiMovie[]>;
  saveByImdbId(imdbId: string, watched: boolean): Promise<ApiMovie>;
  saveAward(awardMovie: ApiMovie, watched: boolean): Promise<ApiMovie>;
  /**
   * Saves a movie identified by free-form query (title, link, imdb_id).
   * BackendLibrary defers to the server's heuristic (translation +
   * fuzzy OMDB lookup); LocalLibrary searches OMDB and saves the first hit.
   */
  addByQuery(query: string): Promise<ApiMovie>;
  patch(id: number, fields: { is_watched?: boolean }): Promise<ApiMovie>;
  remove(id: number): Promise<void>;
  importFromInstagram(url: string): Promise<ApiMovie[]>;
}

// ── BackendLibrary ───────────────────────────────────────────────────────────

class BackendLibrary implements MovieLibrary {
  readonly isGuest = false;

  list() {
    return apiListMovies();
  }

  async saveByImdbId(imdbId: string, watched: boolean): Promise<ApiMovie> {
    const saved = await addMovieByImdbId(imdbId);
    if (watched && saved.id) {
      return apiPatchMovie(saved.id, { is_watched: true });
    }
    return saved;
  }

  saveAward(awardMovie: ApiMovie, watched: boolean) {
    return apiSaveToLibrary(awardMovie.id, watched);
  }

  addByQuery(query: string) {
    return apiAddMovie(query);
  }

  patch(id: number, fields: { is_watched?: boolean }) {
    return apiPatchMovie(id, fields);
  }

  remove(id: number) {
    return apiDeleteMovie(id);
  }

  importFromInstagram(url: string) {
    return apiImportFromInstagram(url);
  }
}

// ── LocalLibrary ─────────────────────────────────────────────────────────────

class LocalLibrary implements MovieLibrary {
  readonly isGuest = true;

  async list(): Promise<ApiMovie[]> {
    return readLocal();
  }

  async saveByImdbId(imdbId: string, watched: boolean): Promise<ApiMovie> {
    const all = readLocal();
    const existing = all.find((m) => m.imdb_id === imdbId);
    if (existing) {
      // already saved — just update watched if changed
      if (existing.is_watched !== watched) {
        existing.is_watched = watched;
        writeLocal(all);
      }
      return existing;
    }
    if (all.length >= LOCAL_LIBRARY_MAX_RECORDS) throw new LocalLibraryFullError();

    const preview = await getMoviePreview(imdbId);
    const record = previewToApiMovie(imdbId, preview, watched);
    all.push(record);
    writeLocal(all);
    return record;
  }

  async addByQuery(query: string): Promise<ApiMovie> {
    const trimmed = query.trim();
    // Direct IMDb id (tt-prefixed) or already-resolved tt: identifier.
    const ttMatch = trimmed.match(/^tt(\d+)/i);
    if (ttMatch) {
      return this.saveByImdbId(ttMatch[0].toLowerCase(), false);
    }
    // For free-form titles or non-Instagram links we lean on OMDB search and
    // pick the top hit. Instagram URLs are routed through importFromInstagram
    // by the caller before this method is reached.
    const results = await searchMovies(trimmed);
    if (results.length === 0) {
      throw new Error('Nothing matches');
    }
    return this.saveByImdbId(results[0].imdb_id, false);
  }

  async saveAward(awardMovie: ApiMovie, watched: boolean): Promise<ApiMovie> {
    const all = readLocal();
    const existing = all.find((m) => m.imdb_id === awardMovie.imdb_id);
    if (existing) {
      existing.is_watched = watched;
      existing.in_library = true;
      writeLocal(all);
      return existing;
    }
    if (all.length >= LOCAL_LIBRARY_MAX_RECORDS) throw new LocalLibraryFullError();

    // Clone + override: the award entry from /api/awards already has full
    // metadata; we just stamp it as in-library and keep the award labels so
    // the awards tab can still mark it as "уже на полке".
    const record: ApiMovie = {
      ...awardMovie,
      id: syntheticId(awardMovie.imdb_id),
      is_watched: watched,
      in_library: true,
      added_at: nowIso(),
    };
    all.push(record);
    writeLocal(all);
    return record;
  }

  async patch(id: number, fields: { is_watched?: boolean }): Promise<ApiMovie> {
    const all = readLocal();
    const movie = all.find((m) => m.id === id);
    if (!movie) throw new Error('Movie not found in local library');
    if (fields.is_watched !== undefined) movie.is_watched = fields.is_watched;
    writeLocal(all);
    return movie;
  }

  async remove(id: number): Promise<void> {
    const all = readLocal();
    const next = all.filter((m) => m.id !== id);
    if (next.length === all.length) throw new Error('Movie not found in local library');
    writeLocal(next);
  }

  async importFromInstagram(url: string): Promise<ApiMovie[]> {
    const parsed = await importFromInstagramParse(url);
    const all = readLocal();
    const seen = new Set(all.map((m) => m.imdb_id));
    const added: ApiMovie[] = [];
    for (const base of parsed) {
      if (seen.has(base.imdb_id)) continue;
      if (all.length + added.length >= LOCAL_LIBRARY_MAX_RECORDS) {
        throw new LocalLibraryFullError();
      }
      added.push(parsedToApiMovie(base));
    }
    if (added.length === 0) return [];
    writeLocal([...all, ...added]);
    return added;
  }
}

// ── Factory ──────────────────────────────────────────────────────────────────

const _backend = new BackendLibrary();
const _local = new LocalLibrary();

export function getLibrary(isGuest: boolean): MovieLibrary {
  return isGuest ? _local : _backend;
}

// ── Guest → registered migration ─────────────────────────────────────────────

/**
 * Drains the local guest library to the backend after a successful
 * register/login/google-login. Returns the number of records imported.
 *
 * On any failure we keep the local copy intact so the user does not lose
 * their list to a transient network error.
 */
export async function migrateGuestLibrary(): Promise<number> {
  const local = readLocal();
  if (local.length === 0) return 0;
  await bulkImportMovies(
    local.map((m) => ({
      imdb_id: m.imdb_id,
      is_watched: m.is_watched,
      rec_source: m.rec_source ?? null,
      rec_note: m.rec_note ?? null,
      source: m.source ?? 'personal',
    })),
  );
  // success — clear local copy
  try {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
  } catch {}
  return local.length;
}
