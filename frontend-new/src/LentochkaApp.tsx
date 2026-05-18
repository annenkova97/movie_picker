import { useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from './auth';
import { useLibrary } from './hooks/useLibrary';
import { recommend } from './api';
import { toUiMovie, type ApiMovie, type UiMovie, type RecSource } from './types';
import {
  TonightMoodFilters,
} from './components/tonight/TonightMoodFilters';
import {
  TonightResults,
} from './components/tonight/TonightResults';
import {
  WatchlistMain,
  SAMPLE_RECS,
  type SavedFilm,
  type RecFilm,
} from './components/watchlist/WatchlistMain';
import {
  WatchlistEmpty,
} from './components/watchlist/WatchlistEmpty';

type View =
  | { name: 'watchlist' }
  | { name: 'tonight-pick' }
  | { name: 'tonight-results'; films: TonightFilm[]; mood: string; duration: string | null };

interface TonightFilm {
  id: string;
  title: string;
  titleAccusative?: string;
  award?: string;
  year: number;
  genre: string;
  runtime: string;
  rating: number;
  rationale: string;
  source: string;
  streaming?: string;
  poster: { background: string; overlay: string; overlayColor?: string };
}

interface Props {
  onOpenAuth: () => void;
  onOpenSettings: () => void;
}

export function LentochkaApp({ onOpenAuth, onOpenSettings }: Props) {
  const auth = useAuth();
  const lib = useLibrary();
  const qc = useQueryClient();
  const moviesQuery = lib.list;

  const uiMovies = useMemo<UiMovie[]>(
    () => (moviesQuery.data ?? []).map(toUiMovie).filter((m) => !m.watched),
    [moviesQuery.data],
  );

  const savedFilms = useMemo<SavedFilm[]>(
    () => uiMovies.map(uiMovieToSavedFilm),
    [uiMovies],
  );

  const [view, setView] = useState<View>({ name: 'watchlist' });
  const [picking, setPicking] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);

  const handleMoodSubmit = async (payload: {
    text: string; genre: string | null; duration: string | null; era: string | null;
  }) => {
    setPicking(true);
    setPickError(null);
    try {
      const query = buildMoodQuery(payload);
      const inlineLibrary = lib.isGuest ? (moviesQuery.data ?? []) : undefined;
      const res = await recommend(query, false, inlineLibrary);
      const films = res.movies.slice(0, 3).map(apiMovieToTonightFilm);
      setView({
        name: 'tonight-results',
        films,
        mood: payload.text || labelForFilters(payload),
        duration: payload.duration,
      });
    } catch (e) {
      setPickError(e instanceof Error ? e.message : String(e));
      // Stay on the picker so the user can retry or close.
    } finally {
      setPicking(false);
    }
  };

  const closeTonight = () => setView({ name: 'watchlist' });

  if (view.name === 'tonight-pick') {
    return (
      <>
        <TonightMoodFilters
          open
          loading={picking}
          onClose={closeTonight}
          onSubmit={handleMoodSubmit}
        />
        {pickError && (
          <div role="alert" style={errorToastStyle}>
            {pickError}
          </div>
        )}
      </>
    );
  }

  if (view.name === 'tonight-results') {
    return (
      <TonightResults
        open
        mood={view.mood}
        duration={view.duration}
        films={view.films}
        onClose={closeTonight}
        onRefine={() => setView({ name: 'tonight-pick' })}
        onLaunch={(film) => {
          // Surface the launch intent — for now just log; will wire to
          // detail view / playback handoff later.
          console.log('[tonight:launch]', film.title);
        }}
      />
    );
  }

  if (uiMovies.length === 0) {
    return (
      <WatchlistEmpty
        userName={auth.user?.name ?? 'друг'}
        curated={SAMPLE_RECS}
        onOpenSettings={onOpenSettings}
        onSave={(rec) => {
          // Curated rec save: relies on the same library hook the old AwardsView
          // used. Stubbed for now since the new RecFilm shape doesn't carry an
          // ApiMovie. Wired up properly when curated catalog ships from backend.
          console.log('[empty:save]', rec.title);
          qc.invalidateQueries({ queryKey: ['library'] });
        }}
        onSelectFilm={(rec) => {
          console.log('[empty:select]', rec.title);
        }}
      />
    );
  }

  return (
    <WatchlistMain
      userName={auth.user?.name ?? 'друг'}
      films={savedFilms}
      recommendations={SAMPLE_RECS}
      onOpenTonight={() => setView({ name: 'tonight-pick' })}
      onOpenSettings={() => {
        if (!auth.user) {
          onOpenAuth();
          return;
        }
        onOpenSettings();
      }}
      onSelectFilm={(film) => {
        console.log('[watchlist:select-film]', film.title);
      }}
      onSelectRec={(rec) => {
        console.log('[watchlist:select-rec]', rec.title);
      }}
      onSeeAllAwards={() => {
        console.log('[watchlist:see-all]');
      }}
    />
  );
}

const errorToastStyle: React.CSSProperties = {
  position: 'fixed',
  bottom: 24,
  left: '50%',
  transform: 'translateX(-50%)',
  zIndex: 200,
  maxWidth: 340,
  padding: '12px 16px',
  borderRadius: 14,
  background: 'rgba(60, 22, 30, 0.95)',
  color: '#F5E6B8',
  border: '1px solid rgba(228, 92, 92, 0.5)',
  fontFamily: 'var(--font-body)',
  fontSize: 13,
  boxShadow: '0 6px 24px rgba(0, 0, 0, 0.5)',
};

// ----- Mappers / utilities -----

function buildMoodQuery(p: {
  text: string; genre: string | null; duration: string | null; era: string | null;
}): string {
  const parts: string[] = [];
  if (p.text) parts.push(p.text);
  if (p.genre) parts.push(`жанр: ${p.genre}`);
  if (p.duration) parts.push(`длительность: ${p.duration}`);
  if (p.era) parts.push(`эпоха: ${p.era}`);
  return parts.length ? parts.join(', ') : 'что-нибудь хорошее на вечер';
}

function labelForFilters(p: { genre: string | null; duration: string | null; era: string | null }): string {
  return [p.genre, p.duration, p.era].filter(Boolean).join(' · ') || 'На вечер';
}

const SOURCE_ICON: Record<RecSource, string> = {
  instagram: '📷',
  telegram: '📢',
  friends: '💬',
  personal: '✦',
};

const SOURCE_LABEL: Record<RecSource, string> = {
  instagram: 'из Instagram',
  telegram: 'из Telegram',
  friends: 'от друга',
  personal: 'личное',
};

function gradientForHue(hue: number): string {
  return `linear-gradient(160deg, hsl(${hue}, 55%, 42%) 0%, hsl(${hue}, 50%, 26%) 50%, hsl(${(hue + 8) % 360}, 60%, 12%) 100%)`;
}

function overlayForTitle(title: string): string {
  // First meaningful word, uppercase, truncated to keep the poster legible.
  const word = title.split(/[\s:—–-]+/)[0] || title;
  return word.toUpperCase().slice(0, 10);
}

function formatRuntime(minutes: number): string {
  if (!minutes || minutes < 1) return '—';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} мин`;
  if (m === 0) return `${h} ч`;
  return `${h} ч ${m} мин`;
}

function uiMovieToSavedFilm(m: UiMovie): SavedFilm {
  const genre = m.genres[0] ?? 'фильм';
  return {
    id: String(m.id),
    title: m.title,
    award: m.award ?? undefined,
    year: m.year ?? 0,
    genre,
    runtime: formatRuntime(m.runtime),
    rating: m.publicRating,
    italic: m.why ?? m.recNote ?? '',
    source: `${SOURCE_ICON[m.recSource]} ${SOURCE_LABEL[m.recSource]}`,
    streaming: undefined,
    poster: m.posterUrl
      ? { background: `center / cover no-repeat url("${m.posterUrl}") , ${gradientForHue(m.hue)}`, overlay: '' }
      : { background: gradientForHue(m.hue), overlay: overlayForTitle(m.title) },
  };
}

function apiMovieToTonightFilm(api: ApiMovie): TonightFilm {
  const ui = toUiMovie(api);
  return {
    id: String(ui.id),
    title: ui.title,
    award: ui.award ?? undefined,
    year: ui.year ?? 0,
    genre: ui.genres[0] ?? 'фильм',
    runtime: formatRuntime(ui.runtime),
    rating: ui.publicRating,
    rationale: ui.why ?? ui.recNote ?? '',
    source: `${SOURCE_ICON[ui.recSource]} ${SOURCE_LABEL[ui.recSource]}`,
    streaming: undefined,
    poster: ui.posterUrl
      ? { background: `center / cover no-repeat url("${ui.posterUrl}") , ${gradientForHue(ui.hue)}`, overlay: '' }
      : { background: gradientForHue(ui.hue), overlay: overlayForTitle(ui.title) },
  };
}

// Re-export shared types for callers that need them.
export type { RecFilm };
