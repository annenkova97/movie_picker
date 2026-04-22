export type RecSource = 'telegram' | 'instagram' | 'friends' | 'personal';

export interface ApiMovie {
  id: number;
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
  is_watched: boolean;
  source: string;
  rec_source?: RecSource | null;
  rec_note?: string | null;
  in_library?: boolean;
  award?: string | null;
  award_year?: number | null;
  added_at: string;
}

export interface UiMovie {
  id: number;
  imdbId: string;
  title: string;
  year: number | null;
  runtime: number;
  director: string;
  cast: string[];
  genres: string[];
  publicRating: number;
  watched: boolean;
  recSource: RecSource;
  recNote: string | null;
  why: string | null;
  plot: string | null;
  plotRu: string | null;
  awardsText: string | null;
  hue: number;
  posterUrl: string | null;
  inLibrary: boolean;
  award: string | null;
  awardYear: number | null;
  addedAt: string;
  savedDaysAgo: number;
}

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function hueFor(m: ApiMovie): number {
  const base = m.imdb_id || String(m.id);
  return hashString(base) % 360;
}

function parseRuntime(awards: string | null): number {
  return 110;
}

function daysBetween(iso: string): number {
  const then = new Date(iso).getTime();
  const now = Date.now();
  return Math.max(0, Math.floor((now - then) / 86_400_000));
}

function normaliseRecSource(s: string | null | undefined, fallback: string): RecSource {
  const v = (s || fallback || 'personal').toLowerCase();
  if (v === 'telegram' || v === 'instagram' || v === 'friends' || v === 'personal') return v;
  return 'personal';
}

function cleanPosterUrl(url: string | null): string | null {
  if (!url) return null;
  const trimmed = url.trim();
  if (!trimmed || trimmed === 'N/A') return null;
  return trimmed;
}

export function toUiMovie(m: ApiMovie): UiMovie {
  const title = m.title;
  return {
    id: m.id,
    imdbId: m.imdb_id,
    title,
    year: m.year,
    runtime: parseRuntime(m.awards),
    director: m.director || '',
    cast: m.cast || [],
    genres: (m.genres || []).map((g) => g.toLowerCase()),
    publicRating: m.imdb_rating ?? 0,
    watched: m.is_watched,
    recSource: normaliseRecSource(m.rec_source, m.source),
    recNote: m.rec_note ?? null,
    why: m.description ?? null,
    plot: m.plot && m.plot !== 'N/A' ? m.plot : null,
    plotRu: m.plot_ru && m.plot_ru !== 'N/A' ? m.plot_ru : null,
    awardsText: m.awards && m.awards !== 'N/A' ? m.awards : null,
    hue: hueFor(m),
    posterUrl: cleanPosterUrl(m.poster_url),
    inLibrary: m.in_library ?? true,
    award: m.award ?? null,
    awardYear: m.award_year ?? null,
    addedAt: m.added_at,
    savedDaysAgo: daysBetween(m.added_at),
  };
}
