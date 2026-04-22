import { useState } from 'react';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import type { RecSource } from '../types';

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

export function QuickAdd({ th, lang, onAdd, loading = false, error }: Props) {
  const [v, setV] = useState('');

  const submit = async () => {
    const q = v.trim();
    if (!q) return;
    await onAdd(q, detectSource(q));
    setV('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <label style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 14, color: th.ink2, fontWeight: 500, letterSpacing: 0.2, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 6, height: 6, borderRadius: 999, background: th.plum }} />
        {T.quickAdd[lang]}
      </label>
      <div style={{ display: 'flex', gap: 10, alignItems: 'stretch', background: th.surface, border: `1px solid ${th.line}`, borderRadius: 14, padding: 6, boxShadow: th.shadow }}>
        <input
          value={v}
          onChange={(e) => setV(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
          placeholder={T.quickAddPh[lang]}
          style={{
            flex: 1, border: 'none', outline: 'none', background: 'transparent',
            fontSize: 16, padding: '14px 14px', color: th.ink, fontFamily: 'inherit',
            minWidth: 0,
          }}
        />
        <button onClick={submit} disabled={loading} style={{
          border: `1px solid ${th.lineStrong}`, background: 'transparent', color: th.ink,
          padding: '0 20px', borderRadius: 10, cursor: loading ? 'wait' : 'pointer',
          fontSize: 14, fontWeight: 600, letterSpacing: 0.2, whiteSpace: 'nowrap',
          opacity: loading ? 0.7 : 1,
        }}>{loading ? '…' : T.save[lang]}</button>
      </div>
      {error && (
        <div style={{ fontSize: 12, color: '#b4442e', fontFamily: 'ui-monospace, monospace' }}>{error}</div>
      )}
    </div>
  );
}
