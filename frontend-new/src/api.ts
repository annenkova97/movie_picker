import type { ApiMovie } from './types';
import { getToken, handleUnauthorized } from './auth';

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { ...init, headers });
  if (res.status === 401) {
    handleUnauthorized();
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    let message = text || `${res.status} ${res.statusText}`;
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed.detail === 'string') message = parsed.detail;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function listMovies(): Promise<ApiMovie[]> {
  return http('/api/movies?in_library=true');
}

export function listAwards(limit?: number): Promise<ApiMovie[]> {
  return http(limit ? `/api/awards?limit=${limit}` : '/api/awards');
}

export function saveToLibrary(id: number, watched = false): Promise<ApiMovie> {
  return http(`/api/movies/${id}/save?is_watched=${watched}`, { method: 'POST' });
}

export function addMovie(query: string): Promise<ApiMovie> {
  return http('/api/movies', { method: 'POST', body: JSON.stringify({ query }) });
}

export interface SearchResult {
  imdb_id: string;
  title: string;
  year: string;
  poster_url: string | null;
}

export interface MoviePreview {
  imdb_id: string;
  title: string;
  year: number | null;
  poster_url: string | null;
  imdb_rating: number | null;
  genres: string[];
  plot: string | null;
  director: string | null;
  cast: string[];
  awards: string | null;
}

export function searchMovies(q: string): Promise<SearchResult[]> {
  return http(`/api/search?q=${encodeURIComponent(q)}`);
}

export function getMoviePreview(imdbId: string): Promise<MoviePreview> {
  return http(`/api/search/preview/${imdbId}`);
}

export function addMovieByImdbId(imdbId: string): Promise<ApiMovie> {
  return http(`/api/movies/by-imdb/${imdbId}`, { method: 'POST' });
}

export function importFromInstagram(url: string): Promise<ApiMovie[]> {
  return http('/api/instagram/import', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

/**
 * Public: parses an Instagram Reel and returns matched movies as MovieBase
 * records (no DB id, no watched flag). Used by the guest library to populate
 * localStorage without an account.
 */
export interface ParsedMovieBase {
  imdb_id: string;
  title: string;
  original_title: string | null;
  year: number | null;
  genres: string[];
  description: string | null;
  plot: string | null;
  plot_ru: string | null;
  cast: string[];
  director: string | null;
  poster_url: string | null;
  imdb_rating: number | null;
  awards: string | null;
}

export function importFromInstagramParse(url: string): Promise<ParsedMovieBase[]> {
  return http('/api/instagram/parse', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

export function patchMovie(id: number, body: { is_watched?: boolean }): Promise<ApiMovie> {
  return http(`/api/movies/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
}

export function deleteMovie(id: number): Promise<void> {
  return http(`/api/movies/${id}`, { method: 'DELETE' });
}

export interface RecommendResult {
  movies: ApiMovie[];
  explanation: string;
}

/**
 * Recommend.
 *
 * If `library` is provided, it is sent inline and the backend uses it as
 * context (no auth required — used in guest mode). Otherwise the backend
 * pulls the authenticated user's library from the DB.
 */
export function recommend(
  query: string,
  includeWatched = false,
  library?: ApiMovie[],
): Promise<RecommendResult> {
  return http('/api/recommend', {
    method: 'POST',
    body: JSON.stringify({
      query,
      include_watched: includeWatched,
      ...(library !== undefined ? { library } : {}),
    }),
  });
}

export interface BulkImportItem {
  imdb_id: string;
  is_watched: boolean;
  rec_source: string | null;
  rec_note: string | null;
  source: string;
}

/**
 * Migrates the local guest library into the authenticated user's account.
 * Backend is idempotent on (user_id, imdb_id) — duplicates are merged, not
 * doubled.
 */
export function bulkImportMovies(items: BulkImportItem[]): Promise<ApiMovie[]> {
  return http('/api/movies/bulk-import', {
    method: 'POST',
    body: JSON.stringify({ items }),
  });
}
