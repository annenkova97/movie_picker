import type { ApiMovie } from './types';

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `${res.status} ${res.statusText}`);
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

export function recommend(query: string, includeWatched = false): Promise<RecommendResult> {
  return http('/api/recommend', {
    method: 'POST',
    body: JSON.stringify({ query, include_watched: includeWatched }),
  });
}
