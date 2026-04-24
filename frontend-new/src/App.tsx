import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { addMovie, deleteMovie, importFromInstagram, listAwards, listMovies, patchMovie, recommend, saveToLibrary } from './api';
import { useAuth } from './auth';
import { AuthScreen } from './components/AuthScreen';
import { Home } from './components/Home';
import { MovieDetail } from './components/MovieDetail';
import { PickReveal } from './components/PickReveal';
import { TopBar } from './components/TopBar';
import type { Lang } from './i18n';
import { T } from './i18n';
import { THEMES, type Theme, type ThemeName } from './theme';
import { toUiMovie, type RecSource, type UiMovie } from './types';

function usePersistent<T extends string>(key: string, fallback: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try { return (localStorage.getItem(key) as T) || fallback; } catch { return fallback; }
  });
  useEffect(() => { try { localStorage.setItem(key, v); } catch {} }, [key, v]);
  return [v, setV];
}

export default function App() {
  const [lang, setLang] = usePersistent<Lang>('lentochka.lang', 'ru');
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

  if (!auth.user) {
    return <AuthScreen th={th} lang={lang} />;
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
  const userId = auth.user?.id;

  const moviesQuery = useQuery({
    queryKey: ['movies', userId],
    queryFn: listMovies,
    enabled: userId != null,
  });

  const awardsQuery = useQuery({
    queryKey: ['awards'],
    queryFn: () => listAwards(),
  });

  const uiMovies = useMemo<UiMovie[]>(
    () => (moviesQuery.data ?? []).map(toUiMovie),
    [moviesQuery.data],
  );

  const libraryIds = useMemo(
    () => new Set(uiMovies.map((m) => m.imdbId)),
    [uiMovies],
  );

  const uiAwards = useMemo<UiMovie[]>(
    () => (awardsQuery.data ?? []).map((m) => {
      const ui = toUiMovie(m);
      // если фильм уже в библиотеке пользователя — отмечаем и копируем статус просмотра
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
  const addMut = useMutation({
    mutationFn: async ({ query, rec }: { query: string; rec: RecSource }) => {
      if (rec === 'instagram') {
        const movies = await importFromInstagram(query);
        return movies[0];
      }
      return addMovie(query);
    },
    onMutate: () => setAddError(null),
    onError: (e: unknown) => setAddError(e instanceof Error ? e.message : String(e)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['movies'] }),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, watched }: { id: number; watched: boolean }) => patchMovie(id, { is_watched: watched }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['movies'] }),
  });

  const removeMut = useMutation({
    mutationFn: (id: number) => deleteMovie(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['movies'] }),
  });

  const saveAwardMut = useMutation({
    mutationFn: ({ id, watched }: { id: number; watched: boolean }) => saveToLibrary(id, watched),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['movies'] });
      qc.invalidateQueries({ queryKey: ['awards'] });
    },
  });

  const [pick, setPick] = useState<{ movie: UiMovie | null; mood: string; explanation: string }>({ movie: null, mood: '', explanation: '' });
  const [detail, setDetail] = useState<UiMovie | null>(null);
  const [picking, setPicking] = useState(false);

  const handlePick = async (mood: string) => {
    setPicking(true);
    try {
      const res = await recommend(mood, false);
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
    // 'tt:' prefix means QuickAdd already saved the movie via addMovieByImdbId — just refresh
    if (query.startsWith('tt:')) {
      qc.invalidateQueries({ queryKey: ['movies'] });
      return;
    }
    await addMut.mutateAsync({ query, rec });
  };

  const handleMovieClick = (m: UiMovie) => {
    setDetail(m);
  };

  const handleToggleWatched = (m: UiMovie) => {
    toggleMut.mutate({ id: m.id, watched: !m.watched });
  };

  return (
    <>
      <TopBar th={th} lang={lang} setLang={setLang} theme={themeName} setTheme={setThemeName} />
      <Home
        th={th}
        lang={lang}
        movies={uiMovies}
        awards={uiAwards}
        loading={moviesQuery.isLoading}
        loadingAwards={awardsQuery.isLoading}
        adding={addMut.isPending}
        picking={picking}
        addError={addError}
        savingAwardId={saveAwardMut.isPending ? (saveAwardMut.variables?.id ?? null) : null}
        onAdd={handleAdd}
        onPick={handlePick}
        onMovieClick={handleMovieClick}
        onToggleWatched={handleToggleWatched}
        onSaveAward={(m, watched) => saveAwardMut.mutate({ id: m.id, watched })}
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
        saving={saveAwardMut.isPending || toggleMut.isPending || removeMut.isPending}
        onClose={() => setDetail(null)}
        onSaveToWatch={(m) => {
          saveAwardMut.mutate({ id: m.id, watched: false });
          setDetail(null);
        }}
        onSaveAsWatched={(m) => {
          saveAwardMut.mutate({ id: m.id, watched: true });
          setDetail(null);
        }}
        onToggleWatched={(m) => {
          handleToggleWatched(m);
          setDetail(null);
        }}
        onRemove={(m) => {
          removeMut.mutate(m.id);
          setDetail(null);
        }}
      />
    </>
  );
}
