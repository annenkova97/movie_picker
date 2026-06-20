import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from './auth';
import { useSettings } from './settings';
import { useLibrary } from './hooks/useLibrary';
import { recommend, listAwards, type WatchAvailability } from './api';
import { track } from './analytics';
import { streamingLabel } from './components/ProviderBadges';
import { T, type Lang } from './i18n';
import { useBooks } from './hooks/useBooks';
import { MovieDetail } from './components/MovieDetail';
import { SearchSheet } from './components/SearchSheet';
import { BooksScreen } from './components/books/BooksScreen';
import { toUiMovie, hueFor, type ApiMovie, type UiMovie, type RecSource } from './types';
import {
  TonightMoodFilters,
} from './components/tonight/TonightMoodFilters';
import {
  TonightResults,
} from './components/tonight/TonightResults';
import {
  WatchlistMain,
  type SavedFilm,
  type RecFilm,
} from './components/watchlist/WatchlistMain';
import {
  WatchlistEmpty,
} from './components/watchlist/WatchlistEmpty';
import { AwardsBrowse } from './components/watchlist/AwardsBrowse';

type View =
  | { name: 'watchlist' }
  | { name: 'tonight-pick' }
  | { name: 'tonight-results'; films: TonightFilm[]; mood: string; duration: string | null }
  | { name: 'awards-all' }
  | { name: 'search' }
  | { name: 'books' };

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
  sourceUrl?: string | null;
  streaming?: string;
  poster: { background: string; overlay: string; overlayColor?: string };
}

interface Props {
  onOpenAuth: () => void;
  onOpenShare: () => void;
}

export function LentochkaApp({ onOpenAuth, onOpenShare }: Props) {
  const auth = useAuth();
  const { lang, region, services } = useSettings();
  const lib = useLibrary();
  const books = useBooks();
  const bookCount = (books.list.data ?? []).length;
  const moviesQuery = lib.list;

  const uiMovies = useMemo<UiMovie[]>(
    () => (moviesQuery.data ?? []).map(toUiMovie).filter((m) => !m.watched),
    [moviesQuery.data],
  );

  const savedFilms = useMemo<SavedFilm[]>(
    () => uiMovies.map((m) => uiMovieToSavedFilm(m, lang)),
    [uiMovies, lang],
  );

  const userName = auth.user?.name ?? T.friend[lang];

  // Real award-winners catalog (replaces the old hardcoded SAMPLE_RECS).
  const awardsQuery = useQuery({ queryKey: ['awards'], queryFn: () => listAwards() });
  const awards = useMemo<ApiMovie[]>(() => awardsQuery.data ?? [], [awardsQuery.data]);
  const recFilms = useMemo<RecFilm[]>(() => awards.map(apiMovieToRecFilm), [awards]);
  // Lookups to recover the source record when a card is tapped.
  const awardApiById = useMemo(() => new Map(awards.map((a) => [String(a.id), a])), [awards]);
  const uiById = useMemo(() => new Map(uiMovies.map((m) => [String(m.id), m])), [uiMovies]);

  const [view, setView] = useState<View>({ name: 'watchlist' });
  const [selected, setSelected] = useState<UiMovie | null>(null);
  const [picking, setPicking] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);

  const detailSaving = lib.saveAward.isPending || lib.patch.isPending || lib.remove.isPending;

  const openSavedDetail = (film: SavedFilm) => {
    const ui = uiById.get(film.id);
    if (ui) setSelected(ui);
  };
  const openAwardDetail = (rec: RecFilm) => {
    const api = awardApiById.get(rec.id);
    if (api) setSelected(toUiMovie(api));
  };
  const saveAwardFromDetail = (m: UiMovie, watched: boolean) => {
    const api = awardApiById.get(String(m.id));
    if (!api) return;
    lib.saveAward.mutateAsync({ movie: api, watched }).finally(() => setSelected(null));
  };

  const handleMoodSubmit = async (payload: {
    text: string; genre: string | null; duration: string | null; era: string | null;
    onlyAvailable: boolean;
  }) => {
    setPicking(true);
    setPickError(null);
    track('recommendation_requested', {
      onlyAvailable: payload.onlyAvailable,
      region,
      hasServices: services.length > 0,
    });
    try {
      const query = buildMoodQuery(payload);
      const inlineLibrary = lib.isGuest ? (moviesQuery.data ?? []) : undefined;
      const res = await recommend(query, false, inlineLibrary, {
        region,
        services,
        onlyAvailable: payload.onlyAvailable,
      });
      const films = res.movies.slice(0, 3).map((m) =>
        apiMovieToTonightFilm(m, lang, res.availability?.[String(m.id)]),
      );
      setView({
        name: 'tonight-results',
        films,
        mood: payload.text || labelForFilters(payload),
        duration: payload.duration,
      });
      track('tonight_pick_viewed', {
        count: films.length,
        onlyAvailable: payload.onlyAvailable,
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
          hasServices={services.length > 0}
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
          // The strongest proxy for "went to actually watch it" — the core
          // signal for the availability experiment.
          track('launch_clicked', { title: film.title, id: film.id });
        }}
      />
    );
  }

  if (view.name === 'search') {
    return <SearchSheet onClose={() => setView({ name: 'watchlist' })} />;
  }

  if (view.name === 'books') {
    return <BooksScreen onBack={() => setView({ name: 'watchlist' })} />;
  }

  const detailModal = (
    <MovieDetail
      lang={lang}
      region={region}
      movie={selected}
      saving={detailSaving}
      onClose={() => setSelected(null)}
      onSaveToWatch={(m) => saveAwardFromDetail(m, false)}
      onSaveAsWatched={(m) => saveAwardFromDetail(m, true)}
      onToggleWatched={(m) => {
        if (!m.watched) track('marked_watched', { id: m.id });
        lib.patch.mutateAsync({ id: m.id, fields: { is_watched: !m.watched } }).finally(() => setSelected(null));
      }}
      onRemove={(m) => lib.remove.mutateAsync(m.id).finally(() => setSelected(null))}
      onSaveDiary={(m, diary) =>
        lib.patch.mutateAsync({
          id: m.id,
          fields: { user_rating: diary.rating, user_note: diary.note },
        }).then(() => undefined)}
    />
  );

  const saveAwardRec = (rec: RecFilm) => {
    const api = awardApiById.get(rec.id);
    if (api) lib.saveAward.mutateAsync({ movie: api, watched: false });
  };

  if (view.name === 'awards-all') {
    return (
      <>
        <AwardsBrowse
          curated={recFilms}
          onBack={() => setView({ name: 'watchlist' })}
          onSave={saveAwardRec}
          onSelect={openAwardDetail}
        />
        {detailModal}
      </>
    );
  }

  if (uiMovies.length === 0) {
    return (
      <>
        <WatchlistEmpty
          userName={userName}
          curated={recFilms}
          bookCount={bookCount}
          onOpenAuth={onOpenAuth}
          onOpenSearch={() => setView({ name: 'search' })}
          onOpenBooks={() => setView({ name: 'books' })}
          onSave={saveAwardRec}
          onSelectFilm={openAwardDetail}
        />
        {detailModal}
      </>
    );
  }

  return (
    <>
      <WatchlistMain
        userName={userName}
        films={savedFilms}
        recommendations={recFilms}
        bookCount={bookCount}
        onOpenTonight={() => setView({ name: 'tonight-pick' })}
        onOpenAuth={onOpenAuth}
        onShare={onOpenShare}
        onOpenSearch={() => setView({ name: 'search' })}
        onOpenBooks={() => setView({ name: 'books' })}
        onSelectFilm={openSavedDetail}
        onSelectRec={openAwardDetail}
        onSeeAllAwards={() => setView({ name: 'awards-all' })}
      />
      {detailModal}
    </>
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

const SOURCE_LABEL_KEY: Record<RecSource, 'recSrcInstagram' | 'recSrcTelegram' | 'recSrcFriends' | 'recSrcPersonal'> = {
  instagram: 'recSrcInstagram',
  telegram: 'recSrcTelegram',
  friends: 'recSrcFriends',
  personal: 'recSrcPersonal',
};

function sourceCaption(src: RecSource, lang: Lang): string {
  // «Личное» (добавлено руками, без источника) не подписываем — подпись
  // источника нужна только когда фильм откуда-то пришёл.
  if (src === 'personal') return '';
  return `${SOURCE_ICON[src]} ${T[SOURCE_LABEL_KEY[src]][lang]}`;
}

function gradientForHue(hue: number): string {
  return `linear-gradient(160deg, hsl(${hue}, 55%, 42%) 0%, hsl(${hue}, 50%, 26%) 50%, hsl(${(hue + 8) % 360}, 60%, 12%) 100%)`;
}

function overlayForTitle(title: string): string {
  // First meaningful word, uppercase, truncated to keep the poster legible.
  const word = title.split(/[\s:—–-]+/)[0] || title;
  return word.toUpperCase().slice(0, 10);
}

function formatRuntime(minutes: number): string {
  // Пустая строка — «не знаем»: карточки просто не показывают сегмент,
  // вместо прежней выдуманной константы 110 минут.
  if (!minutes || minutes < 1) return '';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} мин`;
  if (m === 0) return `${h} ч`;
  return `${h} ч ${m} мин`;
}

function runtimeCaption(minutes: number, isSeries: boolean): string {
  const base = formatRuntime(minutes);
  if (!base) return '';
  // У сериалов OMDB отдаёт длительность эпизода.
  return isSeries ? `${base} / серия` : base;
}

function uiMovieToSavedFilm(m: UiMovie, lang: Lang): SavedFilm {
  const genre = m.genres[0] ?? (lang === 'ru' ? 'фильм' : 'film');
  return {
    id: String(m.id),
    title: m.title,
    award: m.award ?? undefined,
    year: m.year ?? 0,
    isSeries: m.isSeries,
    genre,
    runtime: runtimeCaption(m.runtime, m.isSeries),
    rating: m.publicRating,
    userRating: m.userRating,
    italic: m.why ?? m.recNote ?? '',
    source: sourceCaption(m.recSource, lang),
    sourceUrl: m.sourceUrl,
    streaming: undefined,
    poster: m.posterUrl
      ? { background: `center / cover no-repeat url("${m.posterUrl}") , ${gradientForHue(m.hue)}`, overlay: '' }
      : { background: gradientForHue(m.hue), overlay: overlayForTitle(m.title) },
  };
}

/** Normalise an OMDB/award-string into a short uppercase badge label. */
function shortAward(award: string | null | undefined): string | undefined {
  if (!award) return undefined;
  if (/palme|cannes/i.test(award)) return "PALME D'OR";
  if (/oscar|academy/i.test(award)) return 'OSCAR';
  if (/golden globe/i.test(award)) return 'GOLDEN GLOBE';
  if (/golden lion|venice/i.test(award)) return 'GOLDEN LION';
  if (/bafta/i.test(award)) return 'BAFTA';
  return award.toUpperCase().slice(0, 14);
}

function apiMovieToRecFilm(api: ApiMovie): RecFilm {
  const ui = toUiMovie(api);
  const hue = hueFor(api);
  return {
    id: String(api.id),
    title: ui.title,
    director: ui.director || '',
    year: ui.year ?? 0,
    award: shortAward(api.award),
    poster: ui.posterUrl
      ? {
          background: `center / cover no-repeat url("${ui.posterUrl}"), ${gradientForHue(hue)}`,
          overlay: '',
        }
      : {
          background: gradientForHue(hue),
          overlay: overlayForTitle(ui.title),
          overlayFont: 'body-caps',
        },
  };
}

function apiMovieToTonightFilm(
  api: ApiMovie,
  lang: Lang,
  availability?: WatchAvailability,
): TonightFilm {
  const ui = toUiMovie(api);
  return {
    id: String(ui.id),
    title: ui.title,
    award: ui.award ?? undefined,
    year: ui.year ?? 0,
    genre: ui.genres[0] ?? (lang === 'ru' ? 'фильм' : 'film'),
    runtime: runtimeCaption(ui.runtime, ui.isSeries),
    rating: ui.publicRating,
    rationale: ui.why ?? ui.recNote ?? '',
    source: sourceCaption(ui.recSource, lang),
    sourceUrl: ui.sourceUrl,
    streaming: streamingLabel(availability),
    poster: ui.posterUrl
      ? { background: `center / cover no-repeat url("${ui.posterUrl}") , ${gradientForHue(ui.hue)}`, overlay: '' }
      : { background: gradientForHue(ui.hue), overlay: overlayForTitle(ui.title) },
  };
}

// Re-export shared types for callers that need them.
export type { RecFilm };
