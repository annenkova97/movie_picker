import { useState } from 'react';
import { useSettings } from '../settings';
import { T } from '../i18n';
import { useBooks } from '../hooks/useBooks';
import { searchBooks, getBookPreview, type BookSearchResult, type BookPreview } from '../api';
import type { ApiBook } from '../types';
import { BookDetail } from './BookDetail';

interface Props {
  onClose: () => void;
}

function previewToApiBook(p: BookPreview): ApiBook {
  return {
    id: 0,
    work_key: p.work_key,
    title: p.title,
    authors: p.authors ?? [],
    year: p.year,
    subjects: p.subjects ?? [],
    description: p.description,
    cover_url: p.cover_url,
    rating: p.rating,
    is_read: false,
    source: 'personal',
    rec_source: 'personal',
    rec_note: null,
    in_library: false,
    added_at: new Date().toISOString(),
  };
}

/** Wine-deep book search. Reuses the Open Library API + useBooks; tapping a
 *  result opens BookDetail (preview) so a single detail+save surface is used. */
export function BookSearchSheet({ onClose }: Props) {
  const { lang } = useSettings();
  const books = useBooks();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<BookSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ApiBook | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const handleSearch = async () => {
    const query = q.trim();
    if (!query) return;
    setSearching(true);
    setError(null);
    setResults(null);
    try {
      const found = await searchBooks(query);
      if (found.length === 0) setError(T.quickNothingFound[lang]);
      else setResults(found);
    } catch (e) {
      setError(e instanceof Error ? e.message : T.quickSearchError[lang]);
    } finally {
      setSearching(false);
    }
  };

  const openDetail = async (r: BookSearchResult) => {
    try {
      const preview = await getBookPreview(r.work_key);
      setSelected(previewToApiBook(preview));
    } catch (e) {
      setError(e instanceof Error ? e.message : T.quickLoadFail[lang]);
    }
  };

  const save = async (workKey: string, isRead: boolean) => {
    setSavingKey(workKey);
    try {
      await books.save.mutateAsync({ workKey, isRead });
      setSelected(null);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : T.quickSaveError[lang]);
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <div className="lt-screen ss-screen">
      <header className="ss-header">
        <button className="ss-back" onClick={onClose} aria-label={T.back[lang]}>←</button>
        <div>
          <div className="ss-eyebrow">{T.bookSearchSub[lang]}</div>
          <h1 className="ss-title">{T.bookSearchTitle[lang]}</h1>
        </div>
      </header>

      <div className="ss-bar">
        <input
          className="ss-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
          placeholder={T.bookSearchPh[lang]}
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
            <div className="ss-row" key={r.work_key}>
              <button className="ss-row__main" onClick={() => openDetail(r)}>
                {r.cover_url
                  ? <img className="ss-poster" src={r.cover_url} alt="" onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden'; }} />
                  : <div className="ss-poster ss-poster--blank" aria-hidden>📖</div>}
                <div className="ss-row__text">
                  <div className="ss-row__title">{r.title}</div>
                  <div className="ss-row__year">{[r.author, r.year].filter(Boolean).join(' · ')}</div>
                </div>
              </button>
              <button
                className="ss-save"
                onClick={() => save(r.work_key, false)}
                disabled={savingKey === r.work_key}
              >
                {savingKey === r.work_key ? '…' : T.bookAddWant[lang]}
              </button>
            </div>
          ))}
        </div>
      )}

      <BookDetail
        lang={lang}
        book={selected}
        saving={books.save.isPending}
        onClose={() => setSelected(null)}
        onSaveWant={(b) => save(b.work_key, false)}
        onSaveRead={(b) => save(b.work_key, true)}
      />
    </div>
  );
}
