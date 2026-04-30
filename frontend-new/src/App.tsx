import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { listAwards, recommend } from './api';
import { useAuth } from './auth';
import { useGuestSignupPrompt, useLibrary } from './hooks/useLibrary';
import { migrateGuestLibrary } from './library';
import { AuthScreen } from './components/AuthScreen';
import { GuestSignupSheet } from './components/GuestSignupSheet';
import { Home } from './components/Home';
import { MovieDetail } from './components/MovieDetail';
import { PickReveal } from './components/PickReveal';
import { TopBar } from './components/TopBar';
import type { Lang } from './i18n';
import { T } from './i18n';
import { THEMES, type Theme, type ThemeName } from './theme';
import { toUiMovie, type ApiMovie, type RecSource, type UiMovie } from './types';

function usePersistent<T extends string>(key: string, fallback: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try { return (localStorage.getItem(key) as T) || fallback; } catch { return fallback; }
  });
  useEffect(() => { try { localStorage.setItem(key, v); } catch {} }, [key, v]);
  return [v, setV];
}

export default function App() {
  const [lang, setLang] = usePersistent<Lang>('lentochka.lang', 'en');
  const [themeName, setThemeName] = usePersistent<ThemeName>('lentochka.theme', 'light');
  const th = THEMES[themeName];
  const auth = useAuth();

  useEffect(() => {
    document.body.style.background = th.bg;
    document.body.style.color = th.ink;
    document.body.style.margin = '0';
    document.body.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif';
  }, [th]);

  if (auth.loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: th.ink3, fontSize: 13 }}>
        {T.authLoading[lang]}
      </div>
    );
  }

  return <AppInner th={th} lang={lang} setLang={setLang} themeName={themeName} setThemeName={setThemeName} />;
}

interface AppInnerProps {
  th: Theme;
  lang: Lang;
  setLang: (l: Lang) => void;
  themeName: ThemeName;
  setThemeName: (t: ThemeName) => void;
}

function AppInner({ th, lang, setLang, themeName, setThemeName }: AppInnerProps) {
  const qc = useQueryClient();
  const auth = useAuth();
  const lib = useLibrary();

  // After a successful login/register, drain any guest data the user accrued
  // before signing in. Idempotent: if there's nothing local, the call is a
  // no-op. We invalidate library cache on success so the freshly imported
  // movies appear without a manual reload.
  useEffect(() => {
    if (!auth.user) return;
    let cancelled = false;
    migrateGuestLibrary()
      .then((count) => {
        if (cancelled) return;
        if (count > 0) qc.invalidateQueries({ queryKey: ['library'] });
      })
      .catch((err) => console.warn('[migrate] guest library migration failed:', err));
    return () => { cancelled = true; };
  }, [auth.user?.id, qc]);

  const awardsQuery = useQuery({
    queryKey: ['awards'],
    queryFn: () => listAwards(),
  });

  const moviesQuery = lib.list;

  const uiMovies = useMemo<UiMovie[]>(
    () => (moviesQuery.data ?? []).map(toUiMovie),
    [moviesQuery.data],
  );

  const uiAwards = useMemo<UiMovie[]>(
    () => (awardsQuery.data ?? []).map((m) => {
      const ui = toUiMovie(m);
      const libraryMovie = uiMovies.find((lm) => lm.imdbId === ui.imdbId);
      if (libraryMovie) {
        ui.inLibrary = true;
        ui.watched = libraryMovie.watched;
      }
      return ui;
    }),
    [awardsQuery.data, uiMovies],
  );

  const [addError, setAddError] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register' | null>(null);
  const guestPrompt = useGuestSignupPrompt(uiMovies.length, lib.isGuest);

  const [pick, setPick] = useState<{ movie: UiMovie | null; mood: string; explanation: string }>(
    { movie: null, mood: '', explanation: '' }
  );
  const [detail, setDetail] = useState<UiMovie | null>(null);
  const [picking, setPicking] = useState(false);

  const handlePick = async (mood: string) => {
    setPicking(true);
    try {
      // For guest, send the local library inline so the recommender has context.
      const inlineLibrary = lib.isGuest ? (moviesQuery.data ?? []) : undefined;
      const res = await recommend(mood, false, inlineLibrary);
      const first = res.movies[0];
      if (first) {
        const ui = toUiMovie(first);
        setPick({ movie: ui, mood, explanation: res.explanation || '' });
      } else {
        setPick({ movie: null, mood, explanation: res.explanation || T.noResults[lang] });
      }
    } catch (e) {
      setPick({ movie: null, mood, explanation: e instanceof Error ? e.message : String(e) });
    } finally {
      setPicking(false);
    }
  };

  const handleAdd = async (query: string, rec: RecSource) => {
    // 'tt:' prefix means QuickAdd already saved the movie via lib.save.mutate —
    // just refresh.
    if (query.startsWith('tt:')) {
      qc.invalidateQueries({ queryKey: ['library'] });
      return;
    }
    setAddError(null);
    try {
      if (rec === 'instagram') {
        await lib.importInstagram.mutateAsync(query);
      } else {
        await lib.addByQuery.mutateAsync(query);
      }
    } catch (e) {
      setAddError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleMovieClick = (m: UiMovie) => {
    setDetail(m);
  };

  const handleToggleWatched = (m: UiMovie) => {
    lib.patch.mutate({ id: m.id, fields: { is_watched: !m.watched } });
  };

  const adding = lib.importInstagram.isPending || lib.addByQuery.isPending;
  const savingAwardId = lib.saveAward.isPending ? (lib.saveAward.variables?.movie.id ?? null) : null;
  const detailSaving = lib.saveAward.isPending || lib.patch.isPending || lib.remove.isPending;

  // Components hand us UiMovie (the rendering view) but lib.saveAward needs the
  // backend ApiMovie shape with full metadata + numeric id. Look up the source
  // record by imdb_id from the most recent fetched data.
  const findApiMovie = (imdbId: string): ApiMovie | undefined => {
    return moviesQuery.data?.find((m) => m.imdb_id === imdbId)
      ?? awardsQuery.data?.find((m) => m.imdb_id === imdbId);
  };

  const handleSaveAward = (m: UiMovie, watched: boolean) => {
    const api = findApiMovie(m.imdbId);
    if (!api) {
      console.warn('[saveAward] no ApiMovie for', m.imdbId);
      return;
    }
    lib.saveAward.mutate({ movie: api, watched });
  };

  return (
    <>
      <TopBar
        th={th}
        lang={lang}
        setLang={setLang}
        theme={themeName}
        setTheme={setThemeName}
        onSignInClick={lib.isGuest ? () => setAuthMode('login') : undefined}
      />
      <Home
        th={th}
        lang={lang}
        movies={uiMovies}
        awards={uiAwards}
        loading={moviesQuery.isLoading}
        loadingAwards={awardsQuery.isLoading}
        adding={adding}
        picking={picking}
        addError={addError}
        savingAwardId={savingAwardId}
        onAdd={handleAdd}
        onPick={handlePick}
        onMovieClick={handleMovieClick}
        onToggleWatched={handleToggleWatched}
        onSaveAward={handleSaveAward}
      />
      <PickReveal
        th={th}
        lang={lang}
        movie={pick.movie}
        mood={pick.mood}
        explanation={pick.explanation}
        onClose={() => setPick({ movie: null, mood: '', explanation: '' })}
        onAgain={() => pick.mood && handlePick(pick.mood)}
      />
      <MovieDetail
        th={th}
        lang={lang}
        movie={detail}
        saving={detailSaving}
        onClose={() => setDetail(null)}
        onSaveToWatch={(m) => {
          handleSaveAward(m, false);
          setDetail(null);
        }}
        onSaveAsWatched={(m) => {
          handleSaveAward(m, true);
          setDetail(null);
        }}
        onToggleWatched={(m) => {
          handleToggleWatched(m);
          setDetail(null);
        }}
        onRemove={(m) => {
          lib.remove.mutate(m.id);
          setDetail(null);
        }}
      />

      {guestPrompt.open && (
        <GuestSignupSheet
          th={th}
          lang={lang}
          onCreate={() => { guestPrompt.dismiss(); setAuthMode('register'); }}
          onSignIn={() => { guestPrompt.dismiss(); setAuthMode('login'); }}
          onSkip={() => guestPrompt.dismiss()}
        />
      )}

      {authMode && (
        <AuthScreen
          th={th}
          lang={lang}
          initialMode={authMode}
          onClose={() => setAuthMode(null)}
        />
      )}
    </>
  );
}
