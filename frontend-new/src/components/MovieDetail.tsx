import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import type { UiMovie } from '../types';
import { TypoPoster } from './TypoPoster';

interface Props {
  th: Theme;
  lang: Lang;
  movie: UiMovie | null;
  saving: boolean;
  onClose: () => void;
  onSaveToWatch?: (m: UiMovie) => void;
  onSaveAsWatched?: (m: UiMovie) => void;
  onToggleWatched?: (m: UiMovie) => void;
  onRemove?: (m: UiMovie) => void;
}

export function MovieDetail({ th, lang, movie, saving, onClose, onSaveToWatch, onSaveAsWatched, onToggleWatched, onRemove }: Props) {
  if (!movie) return null;

  const meta = [
    movie.director,
    movie.year,
    `${movie.runtime} ${T.min[lang]}`,
    movie.publicRating > 0 ? `★ ${movie.publicRating.toFixed(1)}` : null,
  ].filter(Boolean).join(' · ');

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed', inset: 0, zIndex: 30,
        background: 'rgba(30,15,25,0.55)',
        backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
        overflowY: 'auto',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: th.surface, borderRadius: 20, padding: 28, maxWidth: 640, width: '100%',
          boxShadow: th.shadowLg, border: `1px solid ${th.line}`,
          display: 'flex', flexDirection: 'column', gap: 20,
          maxHeight: 'calc(100vh - 40px)', overflowY: 'auto',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ minWidth: 0 }}>
            {movie.award && (
              <div style={{ fontSize: 10, fontFamily: 'ui-monospace,monospace', color: th.ink3, textTransform: 'uppercase', letterSpacing: 0.8 }}>
                ✦ {movie.award}{movie.awardYear ? ` · ${movie.awardYear}` : ''}
              </div>
            )}
            <h2 style={{
              margin: '4px 0 0', fontFamily: "'Fraunces', serif", fontWeight: 700,
              fontSize: 28, lineHeight: 1.05, color: th.ink, letterSpacing: -0.4,
            }}>{movie.title}</h2>
            <div style={{ fontSize: 13, color: th.ink3, marginTop: 6, fontFamily: 'ui-monospace,monospace' }}>{meta}</div>
          </div>
          <button
            onClick={onClose}
            aria-label="close"
            style={{
              border: 'none', background: 'transparent', color: th.ink3, fontSize: 26,
              cursor: 'pointer', padding: 0, width: 32, height: 32, lineHeight: 1, flexShrink: 0,
            }}
          >×</button>
        </div>

        <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <TypoPoster movie={movie} lang={lang} w={160} h={240} />
          <div style={{ flex: '1 1 260px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Section title={T.detailPlot[lang]} th={th}>
              <div style={{ fontSize: 14, color: th.ink, lineHeight: 1.5 }}>
                {(lang === 'ru' ? (movie.plotRu || movie.plot) : movie.plot) || movie.why || (
                  <span style={{ color: th.ink3, fontStyle: 'italic' }}>{T.detailNoPlot[lang]}</span>
                )}
              </div>
            </Section>

            {movie.cast.length > 0 && (
              <Section title={T.detailCast[lang]} th={th}>
                <div style={{ fontSize: 13, color: th.ink2, lineHeight: 1.45 }}>
                  {movie.cast.slice(0, 6).join(' · ')}
                </div>
              </Section>
            )}

            {movie.awardsText && !movie.award && (
              <Section title={T.detailAwards[lang]} th={th}>
                <div style={{ fontSize: 13, color: th.ink2, lineHeight: 1.45 }}>{movie.awardsText}</div>
              </Section>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', borderTop: `1px solid ${th.line}`, paddingTop: 18 }}>
          {!movie.inLibrary && onSaveToWatch && (
            <button onClick={() => onSaveToWatch(movie)} disabled={saving} style={{
              border: 'none', background: th.plum, color: th.plumInk,
              padding: '10px 16px', borderRadius: 10, cursor: saving ? 'wait' : 'pointer',
              fontSize: 13, fontWeight: 600, letterSpacing: 0.2, opacity: saving ? 0.7 : 1,
            }}>{T.addToWatch[lang]}</button>
          )}
          {!movie.inLibrary && onSaveAsWatched && (
            <button onClick={() => onSaveAsWatched(movie)} disabled={saving} style={{
              border: `1px solid ${th.lineStrong}`, background: 'transparent', color: th.ink,
              padding: '10px 16px', borderRadius: 10, cursor: saving ? 'wait' : 'pointer',
              fontSize: 13, fontWeight: 500, opacity: saving ? 0.7 : 1,
            }}>{T.addToWatched[lang]}</button>
          )}
          {movie.inLibrary && onToggleWatched && (
            <button onClick={() => onToggleWatched(movie)} style={{
              border: `1px solid ${th.line}`, background: 'transparent', color: th.ink2,
              padding: '10px 16px', borderRadius: 10, cursor: 'pointer',
              fontSize: 13, fontWeight: 500,
            }}>{movie.watched ? `↺ ${T.unwatch[lang]}` : `✓ ${T.markWatched[lang]}`}</button>
          )}
          {movie.inLibrary && onRemove && (
            <button
              onClick={() => {
                const msg = lang === 'ru'
                  ? `Удалить «${movie.title}» из списка?`
                  : `Remove "${movie.title}" from your list?`;
                if (window.confirm(msg)) onRemove(movie);
              }}
              disabled={saving}
              style={{
                border: `1px solid ${th.line}`, background: 'transparent', color: '#b4442e',
                padding: '10px 14px', borderRadius: 10, cursor: saving ? 'wait' : 'pointer',
                fontSize: 13, fontWeight: 500, opacity: saving ? 0.7 : 1,
              }}
            >✕ {T.remove[lang]}</button>
          )}

          <div style={{ flex: 1 }} />

          <a
            href={`https://www.imdb.com/title/${movie.imdbId}/`}
            target="_blank"
            rel="noreferrer noopener"
            style={{
              fontSize: 12, color: th.ink3, textDecoration: 'none',
              fontFamily: 'ui-monospace,monospace', letterSpacing: 0.3,
              borderBottom: `1px dashed ${th.line}`, paddingBottom: 2,
            }}
          >↗ {T.detailImdb[lang]}</a>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children, th }: { title: string; children: React.ReactNode; th: Theme }) {
  return (
    <div>
      <div style={{
        fontSize: 10, fontFamily: 'ui-monospace,monospace', color: th.ink3,
        textTransform: 'uppercase', letterSpacing: 0.7, marginBottom: 6,
      }}>{title}</div>
      {children}
    </div>
  );
}
