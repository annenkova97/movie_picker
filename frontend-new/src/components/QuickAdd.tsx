import { useEffect, useRef, useState } from 'react';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import type { RecSource } from '../types';
import { searchMovies, addMovieByImdbId, addMovie } from '../api';
import type { SearchResult } from '../api';

interface Props {
  th: Theme;
  lang: Lang;
  onAdd: (query: string, recSource: RecSource) => Promise<void> | void;
  loading?: boolean;
  error?: string | null;
}

function detectSource(input: string): RecSource {
  const s = input.toLowerCase();
  if (/instagram|reel/.test(s)) return 'instagram';
  if (/t\.me|telegram/.test(s)) return 'telegram';
  return 'personal';
}

function isLink(input: string): boolean {
  return /^https?:\/\//.test(input.trim()) || /instagram|t\.me|telegram/.test(input.toLowerCase());
}

export function QuickAdd({ th, lang, onAdd, loading = false, error }: Props) {
  const [v, setV] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [saving, setSaving] = useState<string | null>(null); // imdb_id being saved
  const [searchError, setSearchError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Reset results when input is cleared
  useEffect(() => {
    if (!v.trim()) {
      setResults(null);
      setSearchError(null);
    }
  }, [v]);

  const handleSearch = async () => {
    const q = v.trim();
    if (!q) return;

    // Links go directly to onAdd (Instagram/Telegram flow)
    if (isLink(q)) {
      const rec = detectSource(q);
      await onAdd(q, rec);
      setV('');
      return;
    }

    setSearching(true);
    setSearchError(null);
    setResults(null);
    try {
      const found = await searchMovies(q);
      if (found.length === 0) {
        // Fallback: try direct add which now has fuzzy logic on the backend
        setSearchError(lang === 'ru'
          ? 'Ничего не нашли. Попробуй уточнить название.'
          : 'Nothing found. Try a different title.');
      } else {
        setResults(found);
      }
    } catch (e: any) {
      setSearchError(e?.message || (lang === 'ru' ? 'Ошибка поиска' : 'Search error'));
    } finally {
      setSearching(false);
    }
  };

  const handleSave = async (r: SearchResult) => {
    setSaving(r.imdb_id);
    try {
      await addMovieByImdbId(r.imdb_id);
      // Trigger refresh via onAdd with a dummy call that signals success
      await onAdd(`tt:${r.imdb_id}`, 'personal');
      setResults(null);
      setV('');
    } catch (e: any) {
      setSearchError(e?.message || (lang === 'ru' ? 'Не удалось сохранить' : 'Could not save'));
    } finally {
      setSaving(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
    if (e.key === 'Escape') { setResults(null); setV(''); }
  };

  const isLoading = loading || searching;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <style>{`
        @keyframes qa-spin { to { transform: rotate(360deg) } }
        @keyframes qa-fadein { from { opacity: 0; transform: translateY(4px) } to { opacity: 1; transform: none } }
      `}</style>

      <div style={{
        display: 'flex', flexDirection: 'column', gap: 12,
        padding: 16, borderRadius: 18,
        border: `1.5px dashed ${th.lineStrong}`,
        background: th.bgAlt,
      }}>
        <div style={{
          display: 'flex', gap: 8, alignItems: 'stretch',
          background: th.surface, border: `1px solid ${th.line}`,
          borderRadius: 12, padding: 4, boxShadow: th.shadow,
        }}>
          <input
            ref={inputRef}
            value={v}
            onChange={(e) => setV(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={T.quickAddPh[lang]}
            disabled={isLoading}
            style={{
              flex: 1, border: 'none', outline: 'none', background: 'transparent',
              fontSize: 15, padding: '12px 14px', color: th.ink, fontFamily: 'inherit',
              minWidth: 0,
            }}
          />
          <button
            onClick={handleSearch}
            disabled={isLoading || !v.trim()}
            style={{
              border: 'none', background: th.plum, color: th.plumInk,
              padding: '0 20px', borderRadius: 9, cursor: isLoading ? 'wait' : 'pointer',
              fontSize: 14, fontWeight: 600, letterSpacing: 0.2, whiteSpace: 'nowrap',
              opacity: isLoading || !v.trim() ? 0.75 : 1,
              display: 'inline-flex', alignItems: 'center', gap: 8,
            }}
          >
            {isLoading && (
              <span style={{
                width: 12, height: 12, borderRadius: 999,
                border: `2px solid ${th.plumInk}`, borderTopColor: 'transparent',
                animation: 'qa-spin 0.8s linear infinite', display: 'inline-block',
              }} />
            )}
            {results ? (lang === 'ru' ? 'Искать снова' : 'Search again') : T.find[lang]}
          </button>
        </div>
        <div style={{
          fontSize: 11.5, color: th.ink3, fontFamily: 'ui-monospace, monospace',
          letterSpacing: 0.2, textAlign: 'center',
        }}>{T.sourceHint[lang]}</div>
      </div>

      {/* Search results */}
      {results && results.length > 0 && (
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 6,
          padding: '10px 12px', borderRadius: 14,
          background: th.surface, border: `1px solid ${th.line}`,
          animation: 'qa-fadein 0.2s ease both',
        }}>
          <div style={{
            fontSize: 10.5, fontFamily: 'ui-monospace,monospace', color: th.ink3,
            textTransform: 'uppercase', letterSpacing: 1.1, marginBottom: 2,
          }}>
            {lang === 'ru' ? `Нашли ${results.length} вариант${results.length === 1 ? '' : 'а'} — выбери нужный:` : `Found ${results.length} — pick one:`}
          </div>
          {results.map((r) => {
            const isSavingThis = saving === r.imdb_id;
            return (
              <div
                key={r.imdb_id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 12px', borderRadius: 10,
                  background: th.bgAlt, border: `1px solid ${th.line}`,
                  cursor: 'pointer',
                }}
              >
                {r.poster_url && (
                  <img
                    src={r.poster_url}
                    alt={r.title}
                    style={{ width: 36, height: 54, objectFit: 'cover', borderRadius: 5, flexShrink: 0 }}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: "'Fraunces',serif", fontWeight: 600, fontSize: 14, color: th.ink, lineHeight: 1.2 }}>{r.title}</div>
                  <div style={{ fontSize: 11, color: th.ink3, fontFamily: 'ui-monospace,monospace', marginTop: 2 }}>{r.year}</div>
                </div>
                <button
                  onClick={() => handleSave(r)}
                  disabled={!!saving}
                  style={{
                    border: 'none', background: th.plum, color: th.plumInk,
                    padding: '7px 14px', borderRadius: 8,
                    fontSize: 12.5, fontWeight: 600, cursor: saving ? 'wait' : 'pointer',
                    opacity: saving && !isSavingThis ? 0.5 : 1, flexShrink: 0,
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                  }}
                >
                  {isSavingThis && (
                    <span style={{
                      width: 10, height: 10, borderRadius: 999,
                      border: `2px solid ${th.plumInk}`, borderTopColor: 'transparent',
                      animation: 'qa-spin 0.8s linear infinite', display: 'inline-block',
                    }} />
                  )}
                  {lang === 'ru' ? '+ Сохранить' : '+ Save'}
                </button>
              </div>
            );
          })}
          <button
            onClick={() => { setResults(null); setV(''); }}
            style={{
              border: 'none', background: 'transparent', color: th.ink3,
              fontSize: 12, cursor: 'pointer', padding: '4px 0', textAlign: 'left',
              fontFamily: 'ui-monospace,monospace',
            }}
          >✕ {lang === 'ru' ? 'Отмена' : 'Cancel'}</button>
        </div>
      )}

      {(searchError || (error && !loading)) && !results && (
        <div style={{ fontSize: 12, color: '#b4442e', fontFamily: 'ui-monospace, monospace' }}>
          {searchError || error}
        </div>
      )}
    </div>
  );
}
