import { useEffect, useState } from 'react';
import { getShare, type SharedListPayload } from '../api';
import { useLibrary } from '../hooks/useLibrary';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import type { ApiMovie } from '../types';

interface Props {
  th: Theme;
  lang: Lang;
  slug: string;
}

export function SharedListView({ th, lang, slug }: Props) {
  const lib = useLibrary();
  const [data, setData] = useState<SharedListPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    getShare(slug)
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch((e) => {
        if (cancelled) return;
        setLoadError(e?.message || T.sharedNotFound[lang]);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [slug, lang]);

  const handleSaveAll = async () => {
    if (!data) return;
    setSaveError(null);
    try {
      await lib.absorbShared.mutateAsync(data.movies);
      setSaved(true);
    } catch (e: any) {
      setSaveError(e?.message || T.sharedSaveError[lang]);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', background: th.bg, color: th.ink,
      padding: '32px 20px 100px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    }}>
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <a
          href="/"
          style={{
            display: 'inline-block', marginBottom: 24,
            color: th.ink3, textDecoration: 'none', fontSize: 13,
            fontFamily: 'ui-monospace,monospace', letterSpacing: 0.4,
          }}
        >← Lentochka</a>

        {loading && (
          <div style={{ color: th.ink3, fontSize: 14 }}>...</div>
        )}

        {!loading && loadError && (
          <div>
            <h1 style={{ fontFamily: "'Fraunces',serif", fontSize: 28, color: th.ink }}>
              {T.sharedNotFound[lang]}
            </h1>
            <a
              href="/"
              style={{
                display: 'inline-block', marginTop: 16,
                background: th.plum, color: th.plumInk,
                padding: '10px 18px', borderRadius: 10, fontWeight: 600,
                textDecoration: 'none', fontSize: 14,
              }}
            >{T.sharedBackHome[lang]}</a>
          </div>
        )}

        {!loading && data && (
          <>
            <div style={{
              fontSize: 11, color: th.ink3, fontFamily: 'ui-monospace,monospace',
              letterSpacing: 1.1, textTransform: 'uppercase', marginBottom: 8,
            }}>
              {T.sharedHeader[lang]}
              {data.owner_name ? ` ${T.sharedFromBy[lang]} ${data.owner_name}` : ''}
              {' · '}
              {T.sharedSavedDate[lang]} {new Date(data.created_at).toLocaleDateString()}
            </div>
            <h1 style={{
              margin: '0 0 8px', fontFamily: "'Fraunces',serif",
              fontSize: 32, fontWeight: 700, color: th.ink, fontStyle: 'italic',
            }}>{data.name}</h1>
            <div style={{ fontSize: 13, color: th.ink3, marginBottom: 24, fontFamily: 'ui-monospace,monospace' }}>
              {data.movies.length} {T.saved[lang]}
            </div>

            {data.movies.length === 0 ? (
              <div style={{ color: th.ink3 }}>{T.sharedEmpty[lang]}</div>
            ) : (
              <>
                <div style={{
                  display: 'grid', gap: 14,
                  gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                }}>
                  {data.movies.map((m) => (
                    <SharedMovieCard key={m.imdb_id} m={m} th={th} />
                  ))}
                </div>

                <div style={{
                  position: 'sticky', bottom: 16, marginTop: 32,
                  display: 'flex', justifyContent: 'center',
                }}>
                  {saved ? (
                    <div style={{
                      background: th.plum, color: th.plumInk,
                      padding: '14px 24px', borderRadius: 999,
                      fontSize: 15, fontWeight: 600,
                      boxShadow: th.shadow,
                    }}>✓ {T.sharedSavedAll[lang]}</div>
                  ) : (
                    <button
                      onClick={handleSaveAll}
                      disabled={lib.absorbShared.isPending}
                      style={{
                        background: th.plum, color: th.plumInk, border: 'none',
                        padding: '14px 28px', borderRadius: 999, fontSize: 15,
                        fontWeight: 600, cursor: lib.absorbShared.isPending ? 'wait' : 'pointer',
                        boxShadow: th.shadow,
                        opacity: lib.absorbShared.isPending ? 0.7 : 1,
                      }}
                    >✦ {T.sharedSaveAll[lang]}</button>
                  )}
                </div>

                {saveError && (
                  <div style={{ marginTop: 12, color: '#b4442e', fontSize: 13, textAlign: 'center' }}>
                    {saveError}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function SharedMovieCard({ m, th }: { m: ApiMovie; th: Theme }) {
  return (
    <div style={{
      background: th.surface, border: `1px solid ${th.line}`,
      borderRadius: 12, overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      {m.poster_url && (
        <img
          src={m.poster_url}
          alt={m.title}
          style={{ width: '100%', aspectRatio: '2 / 3', objectFit: 'cover' }}
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
      )}
      <div style={{ padding: '10px 12px 12px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{
          fontFamily: "'Fraunces',serif", fontWeight: 600, fontSize: 15,
          color: th.ink, lineHeight: 1.25,
        }}>{m.title}</div>
        <div style={{ fontSize: 11, color: th.ink3, fontFamily: 'ui-monospace,monospace' }}>
          {m.year ?? ''}
          {m.imdb_rating != null ? ` · ⭐ ${m.imdb_rating.toFixed(1)}` : ''}
        </div>
        {m.director && (
          <div style={{ fontSize: 11.5, color: th.ink3 }}>{m.director}</div>
        )}
      </div>
    </div>
  );
}
