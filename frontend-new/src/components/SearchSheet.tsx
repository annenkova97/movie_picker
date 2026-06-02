import { useState } from 'react';
import { useSettings } from '../settings';
import { T } from '../i18n';
import { useLibrary } from '../hooks/useLibrary';
import { searchMovies, getMoviePreview, type SearchResult, type MoviePreview } from '../api';
import { toUiMovie, type ApiMovie, type UiMovie } from '../types';
import { MovieDetail } from './MovieDetail';

interface Props {
  onClose: () => void;
}

function previewToUiMovie(p: MoviePreview): UiMovie {
  const api: ApiMovie = {
    id: 0,
    imdb_id: p.imdb_id,
    title: p.title,
    original_title: null,
    year: p.year,
    genres: p.genres ?? [],
    description: null,
    plot: p.plot,
    plot_ru: null,
    cast: p.cast ?? [],
    director: p.director,
    poster_url: p.poster_url,
    imdb_rating: p.imdb_rating,
    awards: p.awards,
    is_watched: false,
    source: 'personal',
    rec_source: 'personal',
    rec_note: null,
    in_library: false,
    award: null,
    award_year: null,
    added_at: new Date().toISOString(),
  };
  return toUiMovie(api);
}

/**
 * Wine-deep search screen. Reuses the existing search/preview API and the
 * shared library hook; tapping a result opens the (restyled) MovieDetail so a
 * single detail+save surface is used everywhere.
 */
export function SearchSheet({ onClose }: Props) {
  const { lang } = useSettings();
  const lib = useLibrary();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<UiMovie | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  const saving = lib.save.isPending;

  const handleSearch = async () => {
    const query = q.trim();
    if (!query) return;
    setSearching(true);
    setError(null);
    setResults(null);
    try {
      const found = await searchMovies(query);
      if (found.length === 0) setError(T.quickNothingFound[lang]);
      else setResults(found);
    } catch (e) {
      setError(e instanceof Error ? e.message : T.quickSearchError[lang]);
    } finally {
      setSearching(false);
    }
  };

  const openDetail = async (r: SearchResult) => {
    try {
      const preview = await getMoviePreview(r.imdb_id);
      setSelected(previewToUiMovie(preview));
    } catch (e) {
      setError(e instanceof Error ? e.message : T.quickLoadFail[lang]);
    }
  };

  const quickSave = async (r: SearchResult, watched: boolean) => {
    setSavingId(r.imdb_id);
    try {
      await lib.save.mutateAsync({ imdbId: r.imdb_id, watched });
      setSelected(null);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : T.quickSaveError[lang]);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="lt-screen ss-screen">
      <header className="ss-header">
        <button className="ss-back" onClick={onClose} aria-label={T.back[lang]}>←</button>
        <div>
          <div className="ss-eyebrow">{T.searchSubtitle[lang]}</div>
          <h1 className="ss-title">{T.searchTitle[lang]}</h1>
        </div>
      </header>

      <div className="ss-bar">
        <input
          className="ss-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
          placeholder={T.quickAddPh[lang]}
          autoFocus
        />
        <button className="ss-find" onClick={handleSearch} disabled={searching || !q.trim()}>
          {searching ? '…' : T.find[lang]}
        </button>
      </div>

      {error && <div className="ss-error">{error}</div>}

      {results && (
        <div className="ss-results">
          {results.map((r) => (
            <div className="ss-row" key={r.imdb_id}>
              <button className="ss-row__main" onClick={() => openDetail(r)}>
                {r.poster_url
                  ? <img className="ss-poster" src={r.poster_url} alt="" onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden'; }} />
                  : <div className="ss-poster ss-poster--blank" aria-hidden>🎬</div>}
                <div className="ss-row__text">
                  <div className="ss-row__title">{r.title}</div>
                  <div className="ss-row__year">{r.year}</div>
                </div>
              </button>
              <button
                className="ss-save"
                onClick={() => quickSave(r, false)}
                disabled={savingId === r.imdb_id}
              >
                {savingId === r.imdb_id ? '…' : T.quickAddToList[lang]}
              </button>
            </div>
          ))}
        </div>
      )}

      <MovieDetail
        lang={lang}
        movie={selected}
        saving={saving}
        onClose={() => setSelected(null)}
        onSaveToWatch={(m) => quickSave({ imdb_id: m.imdbId, title: m.title, year: String(m.year ?? ''), poster_url: m.posterUrl }, false)}
        onSaveAsWatched={(m) => quickSave({ imdb_id: m.imdbId, title: m.title, year: String(m.year ?? ''), poster_url: m.posterUrl }, true)}
      />
    </div>
  );
}
