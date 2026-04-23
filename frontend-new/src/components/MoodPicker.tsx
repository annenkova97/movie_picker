import { useState } from 'react';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';

interface Props {
  th: Theme;
  lang: Lang;
  onPick: (mood: string) => void;
  loading?: boolean;
}

export function MoodPicker({ th, lang, onPick, loading = false }: Props) {
  const [text, setText] = useState('');
  const [genre, setGenre] = useState<string | null>(null);
  const [duration, setDuration] = useState<string | null>(null);
  const [era, setEra] = useState<string | null>(null);

  const chips = T.moodChips[lang];
  const genres = T.moodGenres[lang];
  const durations = T.moodDurations[lang];
  const eras = T.moodEras[lang];

  const buildQuery = (overrideText?: string) => {
    const base = (overrideText ?? text).trim();
    const parts: string[] = [];
    if (base) parts.push(base);
    if (genre) parts.push(lang === 'ru' ? `жанр: ${genre}` : `genre: ${genre}`);
    if (duration) parts.push(lang === 'ru' ? `длительность: ${duration}` : `length: ${duration}`);
    if (era) parts.push(lang === 'ru' ? `эпоха: ${era}` : `era: ${era}`);
    return parts.length ? parts.join(', ') : chips[0];
  };

  const submit = (overrideText?: string) => {
    const q = buildQuery(overrideText);
    if (!q.trim()) return;
    onPick(q);
  };

  const sectionLabel = (label: string) => (
    <div style={{
      fontSize: 10.5, fontFamily: 'ui-monospace,monospace', color: th.ink3,
      textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 6, marginTop: 4,
    }}>{label}</div>
  );

  const chip = (
    label: string,
    active: boolean,
    onClick: () => void,
  ) => (
    <button
      key={label}
      onClick={onClick}
      style={{
        border: `1px solid ${active ? th.plum : th.line}`,
        background: active ? th.plum : 'transparent',
        color: active ? th.plumInk : th.ink2,
        padding: '6px 12px', borderRadius: 999, cursor: 'pointer',
        fontSize: 12.5, fontFamily: 'inherit', fontWeight: active ? 600 : 400,
        letterSpacing: 0.1, transition: 'all 0.12s',
        whiteSpace: 'nowrap',
      }}
    >{label}</button>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Mood text input */}
      <div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'stretch', background: th.surface, border: `1px solid ${th.line}`, borderRadius: 14, padding: 6, boxShadow: th.shadow }}>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder={T.moodPh[lang]}
            style={{
              flex: 1, border: 'none', outline: 'none', background: 'transparent',
              fontSize: 16, padding: '12px 14px', color: th.ink, fontFamily: 'inherit',
              minWidth: 0,
            }}
          />
          <button
            onClick={() => submit()}
            disabled={loading}
            style={{
              border: 'none', background: th.plum, color: th.plumInk,
              padding: '0 20px', borderRadius: 10, cursor: loading ? 'wait' : 'pointer',
              fontSize: 14, fontWeight: 600, letterSpacing: 0.2, whiteSpace: 'nowrap',
              opacity: loading ? 0.7 : 1,
            }}
          >{loading ? '…' : `${T.pick[lang]} →`}</button>
        </div>

        {/* Quick mood chips */}
        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 8 }}>
          {chips.map((c) =>
            chip(c, false, () => { setText(c); submit(c); })
          )}
        </div>
      </div>

      <div style={{ height: 1, background: th.line }} />

      {/* Genre */}
      <div>
        {sectionLabel(T.moodGenreLabel[lang])}
        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
          {chip(T.moodAnyOption[lang], genre === null, () => setGenre(null))}
          {genres.map((g) =>
            chip(g, genre === g, () => setGenre(genre === g ? null : g))
          )}
        </div>
      </div>

      {/* Duration */}
      <div>
        {sectionLabel(T.moodDurationLabel[lang])}
        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
          {chip(T.moodAnyOption[lang], duration === null, () => setDuration(null))}
          {durations.map((d) =>
            chip(d, duration === d, () => setDuration(duration === d ? null : d))
          )}
        </div>
      </div>

      {/* Era */}
      <div>
        {sectionLabel(T.moodEraLabel[lang])}
        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
          {chip(T.moodAnyOption[lang], era === null, () => setEra(null))}
          {eras.map((e) =>
            chip(e, era === e, () => setEra(era === e ? null : e))
          )}
        </div>
      </div>

      {/* Summary + submit if something selected */}
      {(genre || duration || era) && (
        <button
          onClick={() => submit()}
          disabled={loading}
          style={{
            border: 'none', background: th.plum, color: th.plumInk,
            padding: '13px 20px', borderRadius: 12, cursor: loading ? 'wait' : 'pointer',
            fontSize: 14, fontWeight: 600, letterSpacing: 0.2,
            opacity: loading ? 0.7 : 1, marginTop: 2,
          }}
        >
          {loading ? '…' : `${T.pick[lang]} →`}
        </button>
      )}
    </div>
  );
}
