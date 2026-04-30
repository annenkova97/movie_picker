import { useState } from 'react';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { UiMovie } from '../types';

interface Props {
  movie: UiMovie;
  lang?: Lang;
  w?: number;
  h?: number;
}

export function TypoPoster({ movie, lang = 'en', w = 160, h = 240 }: Props) {
  const [imgFailed, setImgFailed] = useState(false);
  const showImage = !!movie.posterUrl && !imgFailed;

  if (showImage) {
    return (
      <div
        data-poster={movie.imdbId}
        style={{
          width: w,
          height: h,
          borderRadius: 8,
          overflow: 'hidden',
          position: 'relative',
          boxShadow: '0 2px 6px rgba(0,0,0,0.18), 0 12px 24px -12px rgba(0,0,0,0.35)',
          background: `oklch(0.22 0.10 ${movie.hue ?? 30})`,
          flexShrink: 0,
        }}
      >
        <img
          src={movie.posterUrl!}
          alt={movie.title}
          loading="lazy"
          onError={() => setImgFailed(true)}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
      </div>
    );
  }

  return <TypoFallback movie={movie} lang={lang} w={w} h={h} />;
}

function TypoFallback({ movie, lang, w, h }: Required<Pick<Props, 'movie' | 'lang' | 'w' | 'h'>>) {
  const hue = movie.hue ?? 30;
  const bg = `oklch(0.30 0.08 ${hue})`;
  const bgB = `oklch(0.22 0.10 ${hue})`;
  const glow = `oklch(0.78 0.12 ${(hue + 20) % 360})`;
  const paper = '#f5e6b8';
  const title = movie.title;
  const year = movie.year ?? '';
  const dir = movie.director;

  let hash = 0;
  for (let i = 0; i < movie.imdbId.length; i++) hash += movie.imdbId.charCodeAt(i);
  const layout = hash % 4;

  const base: React.CSSProperties = {
    width: w,
    height: h,
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
    boxShadow: '0 2px 6px rgba(0,0,0,0.18), 0 12px 24px -12px rgba(0,0,0,0.35)',
    background: `linear-gradient(160deg, ${bg} 0%, ${bgB} 100%)`,
    color: paper,
    flexShrink: 0,
  };

  const fontStack = `'Fraunces', 'Playfair Display', Georgia, serif`;
  const monoStack = `'JetBrains Mono', ui-monospace, Menlo, monospace`;
  const rating = movie.publicRating > 0 ? movie.publicRating.toFixed(1) : '—';
  const runtimeLabel = `${movie.runtime} ${T.min[lang]}`;

  let content: React.ReactNode;
  if (layout === 0) {
    content = (
      <>
        <div style={{ position: 'absolute', top: 10, left: 12, right: 12, display: 'flex', justifyContent: 'space-between', fontFamily: monoStack, fontSize: Math.max(8, w * 0.055), letterSpacing: 0.5, opacity: 0.8 }}>
          <span>№{String(hash % 99).padStart(2, '0')}</span>
          <span>{year}</span>
        </div>
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '12px 12px 14px', background: `linear-gradient(0deg, ${bgB} 10%, transparent 100%)` }}>
          <div style={{ fontFamily: fontStack, fontWeight: 700, fontSize: Math.max(14, w * 0.13), lineHeight: 0.95, letterSpacing: -0.5, color: paper, textWrap: 'balance' } as React.CSSProperties}>{title}</div>
          {dir && <div style={{ fontFamily: monoStack, fontSize: Math.max(8, w * 0.05), opacity: 0.7, marginTop: 6, letterSpacing: 0.4 }}>{dir}</div>}
        </div>
      </>
    );
  } else if (layout === 1) {
    content = (
      <>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 14, textAlign: 'center' }}>
          <div style={{ fontFamily: fontStack, fontWeight: 600, fontStyle: 'italic', fontSize: Math.max(14, w * 0.14), lineHeight: 1.0, color: paper, textWrap: 'balance' } as React.CSSProperties}>{title}</div>
        </div>
        <div style={{ position: 'absolute', top: 10, left: 12, right: 12, display: 'flex', justifyContent: 'space-between', fontFamily: monoStack, fontSize: Math.max(8, w * 0.05), opacity: 0.7 }}>
          <span>{dir}</span><span>{year}</span>
        </div>
        <div style={{ position: 'absolute', bottom: 10, left: 12, right: 12, borderTop: `1px solid ${paper}33`, paddingTop: 6, fontFamily: monoStack, fontSize: Math.max(8, w * 0.05), opacity: 0.75, display: 'flex', justifyContent: 'space-between' }}>
          <span>{runtimeLabel}</span>
          <span>★ {rating}</span>
        </div>
      </>
    );
  } else if (layout === 2) {
    content = (
      <>
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '48%', display: 'flex', alignItems: 'flex-end', padding: 12 }}>
          <div style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', fontFamily: fontStack, fontWeight: 700, fontSize: Math.max(14, w * 0.14), lineHeight: 0.95, color: paper, letterSpacing: -0.3 } as React.CSSProperties}>{title}</div>
        </div>
        <div style={{ position: 'absolute', right: 12, top: 12, width: '46%', textAlign: 'right', fontFamily: monoStack, fontSize: Math.max(8, w * 0.05), opacity: 0.75, lineHeight: 1.5 }}>
          <div>{year}</div>
          <div>{dir}</div>
          <div style={{ marginTop: 6 }}>★ {rating}</div>
        </div>
        <div style={{ position: 'absolute', right: 12, bottom: 12, width: '46%', textAlign: 'right', fontFamily: monoStack, fontSize: Math.max(8, w * 0.05), opacity: 0.7 }}>
          {runtimeLabel}
        </div>
      </>
    );
  } else {
    content = (
      <>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: '38%', background: `linear-gradient(135deg, ${glow} 0%, ${bg} 100%)`, opacity: 0.65 }} />
        <div style={{ position: 'absolute', top: 12, left: 12, right: 12, fontFamily: monoStack, fontSize: Math.max(8, w * 0.05), opacity: 0.9, letterSpacing: 0.5 }}>{year} · {movie.runtime}&apos;</div>
        <div style={{ position: 'absolute', top: '38%', left: 12, right: 12, borderTop: `1px solid ${paper}55`, paddingTop: 10, fontFamily: fontStack, fontWeight: 700, fontSize: Math.max(14, w * 0.14), lineHeight: 0.95, color: paper, textWrap: 'balance' } as React.CSSProperties}>{title}</div>
        {dir && <div style={{ position: 'absolute', bottom: 10, left: 12, right: 12, fontFamily: monoStack, fontSize: Math.max(8, w * 0.05), opacity: 0.7, letterSpacing: 0.3 }}>{dir}</div>}
      </>
    );
  }

  return <div style={base} data-poster={movie.imdbId}>{content}</div>;
}
