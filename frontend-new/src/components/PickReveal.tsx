import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import type { UiMovie } from '../types';
import { TypoPoster } from './TypoPoster';

interface Props {
  th: Theme;
  lang: Lang;
  movie: UiMovie | null;
  mood?: string;
  explanation?: string;
  onClose: () => void;
  onAgain: () => void;
}

export function PickReveal({ th, lang, movie, mood, explanation, onClose, onAgain }: Props) {
  if (!movie) return null;
  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 20,
        background: 'rgba(30,15,25,0.55)',
        backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
      }}
      onClick={onClose}
    >
      <div onClick={(e) => e.stopPropagation()} style={{
        background: th.surface, borderRadius: 20, padding: 24, maxWidth: 460, width: '100%',
        boxShadow: th.shadowLg, border: `1px solid ${th.line}`,
        display: 'flex', flexDirection: 'column', gap: 18,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 10, fontFamily: 'ui-monospace,monospace', color: th.ink3, textTransform: 'uppercase', letterSpacing: 0.8 }}>{T.pickHeader[lang]}</div>
            {mood && <div style={{ fontSize: 13, color: th.ink2, marginTop: 4, fontStyle: 'italic' }}>«{mood}»</div>}
          </div>
          <button onClick={onClose} style={{
            border: 'none', background: 'transparent', color: th.ink3, fontSize: 22,
            cursor: 'pointer', padding: 0, width: 28, height: 28, lineHeight: 1,
          }}>×</button>
        </div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <TypoPoster movie={movie} lang={lang} w={140} h={210} />
          <div style={{ flex: 1, minWidth: 0, paddingTop: 4 }}>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 24, color: th.ink, lineHeight: 1.05 } as React.CSSProperties}>{movie.title}</div>
            <div style={{ fontSize: 13, color: th.ink3, marginTop: 6 }}>{[movie.director, movie.year, `${movie.runtime} ${T.min[lang]}`].filter(Boolean).join(' · ')}</div>
            {(explanation || movie.why) && (
              <div style={{ marginTop: 14, padding: '12px 14px', background: th.bgAlt, borderRadius: 10, border: `1px solid ${th.line}` }}>
                <div style={{ fontSize: 10, fontFamily: 'ui-monospace,monospace', color: th.ink3, textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 4 }}>{T.pickBecause[lang]}</div>
                <div style={{ fontSize: 13, color: th.ink, lineHeight: 1.45 }}>{explanation || movie.why}</div>
              </div>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
          <button onClick={onAgain} style={{
            flex: 1, border: `1px solid ${th.line}`, background: 'transparent', color: th.ink,
            padding: '11px', borderRadius: 10, cursor: 'pointer', fontSize: 13, fontWeight: 600,
          }}>↻ {T.pickAgain[lang]}</button>
          <button onClick={onClose} style={{
            flex: 2, border: 'none', background: th.plum, color: th.plumInk,
            padding: '11px', borderRadius: 10, cursor: 'pointer', fontSize: 13, fontWeight: 600,
          }}>▸ {T.pickWatch[lang]}</button>
        </div>
      </div>
    </div>
  );
}
