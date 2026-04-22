import { useMemo, useState } from 'react';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import type { UiMovie } from '../types';
import { TypoPoster } from './TypoPoster';

interface Props {
  th: Theme;
  lang: Lang;
  movies: UiMovie[];
  loading: boolean;
  savingId: number | null;
  onSave: (m: UiMovie, watched: boolean) => void;
  onOpen: (m: UiMovie) => void;
}

export function AwardsView({ th, lang, movies, loading, savingId, onSave, onOpen }: Props) {
  const awards = useMemo(() => {
    const set = new Set<string>();
    movies.forEach((m) => { if (m.award) set.add(m.award); });
    return Array.from(set);
  }, [movies]);
  const [filter, setFilter] = useState<string | null>(null);

  const visible = filter ? movies.filter((m) => m.award === filter) : movies;

  if (loading) {
    return (
      <div style={{ padding: '0 40px 40px', color: th.ink3, fontFamily: 'ui-monospace,monospace', fontSize: 12, maxWidth: 1200, margin: '0 auto' }}>
        {T.loading[lang]}
      </div>
    );
  }

  if (movies.length === 0) {
    return (
      <div style={{ padding: '0 40px 40px', color: th.ink3, fontSize: 13, maxWidth: 1200, margin: '0 auto' }}>
        {T.awardsEmpty[lang]}
      </div>
    );
  }

  return (
    <div style={{ padding: '0 40px 40px', display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <FilterChip active={filter === null} onClick={() => setFilter(null)} th={th} label={lang === 'ru' ? 'Все' : 'All'} />
        {awards.map((a) => (
          <FilterChip key={a} active={filter === a} onClick={() => setFilter(a)} th={th} label={a} />
        ))}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
        gap: 18,
      }}>
        {visible.map((m) => (
          <AwardCard key={m.id} m={m} th={th} lang={lang} saving={savingId === m.id} onSave={onSave} onOpen={onOpen} />
        ))}
      </div>
    </div>
  );
}

function FilterChip({ active, onClick, th, label }: { active: boolean; onClick: () => void; th: Theme; label: string }) {
  return (
    <button onClick={onClick} style={{
      border: `1px solid ${active ? th.plum : th.line}`,
      background: active ? th.plum : 'transparent',
      color: active ? th.plumInk : th.ink2,
      padding: '7px 14px', borderRadius: 999, cursor: 'pointer',
      fontSize: 12.5, fontFamily: 'inherit', fontWeight: 500, letterSpacing: 0.2,
    }}>{label}</button>
  );
}

function AwardCard({ m, th, lang, saving, onSave, onOpen }: { m: UiMovie; th: Theme; lang: Lang; saving: boolean; onSave: (m: UiMovie, watched: boolean) => void; onOpen: (m: UiMovie) => void }) {
  const alreadySaved = m.inLibrary;
  const stop = (e: React.MouseEvent) => e.stopPropagation();
  return (
    <div
      onClick={() => onOpen(m)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(m); } }}
      style={{
        display: 'flex', flexDirection: 'column', gap: 10,
        padding: 12, borderRadius: 14,
        background: th.surface, border: `1px solid ${th.line}`,
        cursor: 'pointer',
      }}
    >
      <TypoPoster movie={m} lang={lang} w={156} h={234} />
      <div>
        <div style={{ fontSize: 9.5, fontFamily: 'ui-monospace,monospace', color: th.ink3, textTransform: 'uppercase', letterSpacing: 0.6 }}>
          {m.award}{m.awardYear ? ` · ${m.awardYear}` : ''}
        </div>
        <div style={{ fontFamily: "'Fraunces',serif", fontWeight: 700, fontSize: 15, color: th.ink, lineHeight: 1.15, marginTop: 3 }}>{m.title}</div>
        <div style={{ fontSize: 11.5, color: th.ink3, marginTop: 2, fontFamily: 'ui-monospace,monospace' }}>{[m.director, m.year].filter(Boolean).join(' · ')}</div>
      </div>
      {alreadySaved ? (
        <div style={{ fontSize: 11.5, color: th.ink3, fontStyle: 'italic', padding: '6px 0' }}>{T.inMyLibrary[lang]}</div>
      ) : (
        <div style={{ display: 'flex', gap: 6 }} onClick={stop}>
          <button onClick={(e) => { e.stopPropagation(); onSave(m, false); }} disabled={saving} style={{
            flex: 2, border: 'none', background: th.plum, color: th.plumInk,
            padding: '8px 10px', borderRadius: 8, cursor: saving ? 'wait' : 'pointer',
            fontSize: 11.5, fontWeight: 600, letterSpacing: 0.2,
            opacity: saving ? 0.7 : 1,
          }}>{T.addToWatch[lang]}</button>
          <button onClick={(e) => { e.stopPropagation(); onSave(m, true); }} disabled={saving} style={{
            flex: 1, border: `1px solid ${th.lineStrong}`, background: 'transparent', color: th.ink,
            padding: '8px 10px', borderRadius: 8, cursor: saving ? 'wait' : 'pointer',
            fontSize: 11.5, fontWeight: 500,
            opacity: saving ? 0.7 : 1,
          }}>{T.addToWatched[lang]}</button>
        </div>
      )}
    </div>
  );
}
