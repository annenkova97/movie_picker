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
  const [v, setV] = useState('');
  const chips = T.moodChips[lang];

  const submit = (value: string) => {
    const m = value.trim();
    if (!m) return;
    onPick(m);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <label style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 14, color: th.ink2, fontWeight: 500, letterSpacing: 0.2, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 6, height: 6, borderRadius: 999, background: th.butter }} />
        {T.mood[lang]}
      </label>
      <div style={{ display: 'flex', gap: 10, alignItems: 'stretch', background: th.surface, border: `1px solid ${th.line}`, borderRadius: 14, padding: 6, boxShadow: th.shadow }}>
        <input
          value={v}
          onChange={(e) => setV(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit(v || chips[0]); }}
          placeholder={T.moodPh[lang]}
          style={{
            flex: 1, border: 'none', outline: 'none', background: 'transparent',
            fontSize: 16, padding: '14px 14px', color: th.ink, fontFamily: 'inherit',
            minWidth: 0,
          }}
        />
        <button onClick={() => submit(v || chips[0])} disabled={loading} style={{
          border: 'none', background: th.plum, color: th.plumInk,
          padding: '0 20px', borderRadius: 10, cursor: loading ? 'wait' : 'pointer',
          fontSize: 14, fontWeight: 600, letterSpacing: 0.2, whiteSpace: 'nowrap',
          opacity: loading ? 0.7 : 1,
        }}>{loading ? '…' : `${T.pick[lang]} →`}</button>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {chips.map((c, i) => (
          <button key={i} onClick={() => { setV(c); submit(c); }} style={{
            border: `1px solid ${th.line}`, background: 'transparent', color: th.ink2,
            padding: '7px 12px', borderRadius: 999, cursor: 'pointer', fontSize: 12.5, fontFamily: 'inherit',
          }}>{c}</button>
        ))}
      </div>
    </div>
  );
}
