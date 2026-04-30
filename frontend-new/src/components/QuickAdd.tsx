import { useEffect, useRef, useState } from 'react';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import type { RecSource } from '../types';
import { searchMovies, getMoviePreview } from '../api';
import type { SearchResult, MoviePreview } from '../api';
import { useLibrary } from '../hooks/useLibrary';

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

// ── Preview Panel ─────────────────────────────────────────────────────────────

interface PreviewPanelProps {
  th: Theme;
  lang: Lang;
  imdbId: string;
  onSaveWatch: () => void;
  onSaveWatched: () => void;
  onClose: () => void;
  saving: boolean;
}

function PreviewPanel({ th, lang, imdbId, onSaveWatch, onSaveWatched, onClose, saving }: PreviewPanelProps) {
  const [preview, setPreview] = useState<MoviePreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    getMoviePreview(imdbId)
      .then((p) => { if (!cancelled) { setPreview(p); setLoading(false); } })
      .catch((e) => { if (!cancelled) { setErr(e?.message || 'error'); setLoading(false); } });
    return () => { cancelled = true; };
  }, [imdbId]);

  return (
    <div style={{
      marginTop: 6,
      borderRadius: 14,
      background: th.surface,
      border: `1px solid ${th.plum}44`,
      overflow: 'hidden',
      animation: 'qa-fadein 0.18s ease both',
    }}>
      {loading && (
        <div style={{ padding: '20px 16px', textAlign: 'center', color: th.ink3, fontSize: 12 }}>
          <span style={{
            display: 'inline-block', width: 14, height: 14, borderRadius: 999,
            border: `2px solid ${th.plum}`, borderTopColor: 'transparent',
            animation: 'qa-spin 0.8s linear infinite', verticalAlign: 'middle', marginRight: 8,
          }} />
          {T.quickLoadingDetails[lang]}
        </div>
      )}

      {err && (
        <div style={{ padding: '12px 16px', fontSize: 12, color: '#b4442e' }}>
          {T.quickLoadFail[lang]}
        </div>
      )}

      {preview && !loading && (
        <div style={{ display: 'flex', gap: 14, padding: 14, alignItems: 'flex-start' }}>
          {/* Poster */}
          {preview.poster_url && (
            <img
              src={preview.poster_url}
              alt={preview.title}
              style={{ width: 72, height: 108, objectFit: 'cover', borderRadius: 8, flexShrink: 0 }}
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}

          {/* Info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontFamily: "'Fraunces',serif", fontWeight: 700, fontSize: 15, color: th.ink, lineHeight: 1.25, marginBottom: 4 }}>
              {preview.title} {preview.year ? <span style={{ fontWeight: 400, color: th.ink3 }}>({preview.year})</span> : null}
            </div>

            {/* Rating + genres row */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8, alignItems: 'center' }}>
              {preview.imdb_rating != null && (
                <span style={{
                  background: '#F59E0B', color: '#000', borderRadius: 6,
                  padding: '2px 7px', fontSize: 12, fontWeight: 700,
                }}>
                  ⭐ {preview.imdb_rating.toFixed(1)}
                </span>
              )}
              {preview.genres.slice(0, 3).map((g) => (
                <span key={g} style={{
                  background: th.bgAlt, border: `1px solid ${th.line}`,
                  borderRadius: 6, padding: '2px 7px', fontSize: 11, color: th.ink2,
                }}>
                  {g}
                </span>
              ))}
            </div>

            {/* Director */}
            {preview.director && (
              <div style={{ fontSize: 12, color: th.ink3, marginBottom: 6 }}>
                {T.quickDirectorPrefix[lang]}
                <span style={{ color: th.ink2, fontWeight: 500 }}>{preview.director}</span>
              </div>
            )}

            {/* Plot */}
            {preview.plot && (
              <div style={{
                fontSize: 12.5, color: th.ink2, lineHeight: 1.5,
                marginBottom: 8,
                display: '-webkit-box', WebkitLineClamp: 4,
                WebkitBoxOrient: 'vertical', overflow: 'hidden',
              }}>
                {preview.plot}
              </div>
            )}

            {/* Awards */}
            {preview.awards && (
              <div style={{ fontSize: 11.5, color: th.ink3, marginBottom: 10, fontStyle: 'italic' }}>
                🏆 {preview.awards}
              </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                onClick={onSaveWatch}
                disabled={saving}
                style={{
                  border: 'none', background: th.plum, color: th.plumInk,
                  padding: '8px 16px', borderRadius: 9, fontSize: 13, fontWeight: 600,
                  cursor: saving ? 'wait' : 'pointer', opacity: saving ? 0.7 : 1,
                }}
              >
                ♥ {T.quickKeep[lang]}
              </button>
              <button
                onClick={onSaveWatched}
                disabled={saving}
                style={{
                  border: `1.5px solid ${th.line}`, background: 'transparent', color: th.ink2,
                  padding: '8px 14px', borderRadius: 9, fontSize: 13, fontWeight: 500,
                  cursor: saving ? 'wait' : 'pointer', opacity: saving ? 0.7 : 1,
                }}
              >
                ✓ {T.quickAlreadyWatched[lang]}
              </button>
              <button
                onClick={onClose}
                disabled={saving}
                style={{
                  border: 'none', background: 'transparent', color: th.ink3,
                  padding: '8px 6px', fontSize: 12, cursor: 'pointer',
                }}
              >
                {T.quickClose[lang]}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main QuickAdd ─────────────────────────────────────────────────────────────

export function QuickAdd({ th, lang, onAdd, loading = false, error }: Props) {
  const lib = useLibrary();
  const [v, setV] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [saving, setSaving] = useState<string | null>(null);          // imdb_id being saved
  const [expandedId, setExpandedId] = useState<string | null>(null);  // which card is expanded
  const [searchError, setSearchError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!v.trim()) {
      setResults(null);
      setSearchError(null);
      setExpandedId(null);
    }
  }, [v]);

  const handleSearch = async () => {
    const q = v.trim();
    if (!q) return;

    if (isLink(q)) {
      const rec = detectSource(q);
      await onAdd(q, rec);
      setV('');
      return;
    }

    setSearching(true);
    setSearchError(null);
    setResults(null);
    setExpandedId(null);
    try {
      const found = await searchMovies(q);
      if (found.length === 0) {
        setSearchError(T.quickNothingFound[lang]);
      } else {
        setResults(found);
      }
    } catch (e: any) {
      setSearchError(e?.message || T.quickSearchError[lang]);
    } finally {
      setSearching(false);
    }
  };

  // Quick save (1 click — "watched: false" by default)
  const handleQuickSave = async (r: SearchResult, e: React.MouseEvent) => {
    e.stopPropagation();
    setSaving(r.imdb_id);
    try {
      await lib.save.mutateAsync({ imdbId: r.imdb_id, watched: false });
      // notify App to refresh + clear UI
      await onAdd(`tt:${r.imdb_id}`, 'personal');
      setResults(null);
      setV('');
      setExpandedId(null);
    } catch (err: any) {
      setSearchError(err?.message || T.quickSaveError[lang]);
    } finally {
      setSaving(null);
    }
  };

  // Save from preview panel (supports watched flag)
  const handlePreviewSave = async (imdbId: string, watched: boolean) => {
    setSaving(imdbId);
    try {
      await lib.save.mutateAsync({ imdbId, watched });
      await onAdd(`tt:${imdbId}`, 'personal');
      setResults(null);
      setV('');
      setExpandedId(null);
    } catch (err: any) {
      setSearchError(err?.message || T.quickSaveError[lang]);
    } finally {
      setSaving(null);
    }
  };

  const handleCardClick = (imdbId: string) => {
    setExpandedId((prev) => (prev === imdbId ? null : imdbId));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
    if (e.key === 'Escape') { setResults(null); setV(''); setExpandedId(null); }
  };

  const isLoading = loading || searching;

  const resultsHint = results && (
    results.length === 1
      ? T.quickResultsHintOne[lang]
      : T.quickResultsHintMany[lang].replace('%n', String(results.length))
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <style>{`
        @keyframes qa-spin { to { transform: rotate(360deg) } }
        @keyframes qa-fadein { from { opacity: 0; transform: translateY(4px) } to { opacity: 1; transform: none } }
      `}</style>

      {/* Search input */}
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
            {results ? T.quickSearchAgain[lang] : T.find[lang]}
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
            {resultsHint}
          </div>

          {results.map((r) => {
            const isSavingThis = saving === r.imdb_id;
            const isExpanded = expandedId === r.imdb_id;
            return (
              <div key={r.imdb_id}>
                {/* Card row */}
                <div
                  onClick={() => handleCardClick(r.imdb_id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 12px', borderRadius: isExpanded ? '10px 10px 0 0' : 10,
                    background: isExpanded ? `${th.plum}11` : th.bgAlt,
                    border: `1px solid ${isExpanded ? th.plum + '55' : th.line}`,
                    cursor: 'pointer',
                    transition: 'background 0.15s, border-color 0.15s',
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
                    <div style={{ fontFamily: "'Fraunces',serif", fontWeight: 600, fontSize: 14, color: th.ink, lineHeight: 1.2 }}>
                      {r.title}
                    </div>
                    <div style={{ fontSize: 11, color: th.ink3, fontFamily: 'ui-monospace,monospace', marginTop: 2 }}>
                      {r.year}
                      {!isExpanded && (
                        <span style={{ marginLeft: 6, color: th.plum, fontSize: 10, fontWeight: 600 }}>
                          {T.quickDetailsToggle[lang]}
                        </span>
                      )}
                    </div>
                  </div>
                  {/* Quick-save button */}
                  <button
                    onClick={(e) => handleQuickSave(r, e)}
                    disabled={!!saving}
                    title={T.quickAddTooltip[lang]}
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
                    {T.quickAddToList[lang]}
                  </button>
                </div>

                {/* Inline preview panel */}
                {isExpanded && (
                  <PreviewPanel
                    th={th}
                    lang={lang}
                    imdbId={r.imdb_id}
                    saving={!!saving}
                    onSaveWatch={() => handlePreviewSave(r.imdb_id, false)}
                    onSaveWatched={() => handlePreviewSave(r.imdb_id, true)}
                    onClose={() => setExpandedId(null)}
                  />
                )}
              </div>
            );
          })}

          <button
            onClick={() => { setResults(null); setV(''); setExpandedId(null); }}
            style={{
              border: 'none', background: 'transparent', color: th.ink3,
              fontSize: 12, cursor: 'pointer', padding: '4px 0', textAlign: 'left',
              fontFamily: 'ui-monospace,monospace',
            }}
          >{T.quickCancel[lang]}</button>
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
