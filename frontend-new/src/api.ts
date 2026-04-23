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

export function importFromInstagram(url: string): Promise<ApiMovie[]> {
  return http('/api/instagram/import', {
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

export function recommend(query: string, includeWatched = false): Promise<RecommendResult> {
  return http('/api/recommend', {
    method: 'POST',
    body: JSON.stringify({ query, include_watched: includeWatched }),
  });
}
