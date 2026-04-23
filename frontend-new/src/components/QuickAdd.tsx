import { useEffect, useRef, useState } from 'react';
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

function stepsFor(source: RecSource, lang: Lang): string[] {
  if (source === 'instagram') {
    return [T.statusOpenReels[lang], T.statusListen[lang], T.statusCaptions[lang], T.statusCollect[lang]];
  }
  if (source === 'telegram') {
    return [T.statusOpenPost[lang], T.statusReadPost[lang], T.statusFindTitle[lang]];
  }
  return [T.statusLookup[lang], T.statusImdb[lang]];
}

export function QuickAdd({ th, lang, onAdd, loading = false, error }: Props) {
  const [v, setV] = useState('');
  const [activeStep, setActiveStep] = useState(0);
  const [loadingSource, setLoadingSource] = useState<RecSource>('personal');
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!loading) {
      if (timerRef.current != null) { window.clearInterval(timerRef.current); timerRef.current = null; }
      setActiveStep(0);
      return;
    }
    const steps = stepsFor(loadingSource, lang);
    setActiveStep(0);
    timerRef.current = window.setInterval(() => {
      setActiveStep((s) => (s + 1 < steps.length ? s + 1 : s));
    }, 1100);
    return () => {
      if (timerRef.current != null) { window.clearInterval(timerRef.current); timerRef.current = null; }
    };
  }, [loading, loadingSource, lang]);

  const submit = async () => {
    const q = v.trim();
    if (!q) return;
    const rec = detectSource(q);
    setLoadingSource(rec);
    await onAdd(q, rec);
    setV('');
  };

  const steps = stepsFor(loadingSource, lang);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <style>{`
        @keyframes lentochka-pulse { 0%,100% { opacity: .35 } 50% { opacity: 1 } }
        @keyframes lentochka-fadein { from { opacity: 0; transform: translateY(3px) } to { opacity: 1; transform: none } }
        @keyframes lentochka-spin { to { transform: rotate(360deg) } }
      `}</style>
      <div style={{
        display: 'flex', flexDirection: 'column', gap: 12,
        padding: 16, borderRadius: 18,
        border: `1.5px dashed ${th.lineStrong}`,
        background: th.bgAlt,
      }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'stretch', background: th.surface, border: `1px solid ${th.line}`, borderRadius: 12, padding: 4, boxShadow: th.shadow }}>
          <input
            value={v}
            onChange={(e) => setV(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder={T.quickAddPh[lang]}
            disabled={loading}
            style={{
              flex: 1, border: 'none', outline: 'none', background: 'transparent',
              fontSize: 15, padding: '12px 14px', color: th.ink, fontFamily: 'inherit',
              minWidth: 0,
            }}
          />
          <button onClick={submit} disabled={loading || !v.trim()} style={{
            border: 'none', background: th.plum, color: th.plumInk,
            padding: '0 20px', borderRadius: 9, cursor: loading ? 'wait' : 'pointer',
            fontSize: 14, fontWeight: 600, letterSpacing: 0.2, whiteSpace: 'nowrap',
            opacity: loading || !v.trim() ? 0.75 : 1,
            display: 'inline-flex', alignItems: 'center', gap: 8,
          }}>
            {loading && (
              <span style={{
                width: 12, height: 12, borderRadius: 999,
                border: `2px solid ${th.plumInk}`, borderTopColor: 'transparent',
                animation: 'lentochka-spin 0.8s linear infinite', display: 'inline-block',
              }} />
            )}
            {T.find[lang]}
          </button>
        </div>
        <div style={{
          fontSize: 11.5, color: th.ink3, fontFamily: 'ui-monospace, monospace',
          letterSpacing: 0.2, textAlign: 'center',
        }}>{T.sourceHint[lang]}</div>
      </div>

      {loading && (
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 6,
          padding: '10px 14px', borderRadius: 10,
          background: th.chipBg, border: `1px dashed ${th.line}`,
        }}>
          {steps.map((s, i) => {
            const done = i < activeStep;
            const active = i === activeStep;
            return (
              <div key={s} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                fontSize: 12.5, fontFamily: 'ui-monospace, monospace',
                color: done ? th.ink2 : active ? th.ink : th.ink3,
                animation: 'lentochka-fadein 0.35s ease both',
                animationDelay: `${i * 90}ms`,
              }}>
                <span style={{
                  width: 14, display: 'inline-flex', justifyContent: 'center',
                  color: done ? th.plum : active ? th.ink : th.ink3,
                  animation: active ? 'lentochka-pulse 1.1s ease-in-out infinite' : undefined,
                }}>
                  {done ? '✓' : active ? '•' : '·'}
                </span>
                <span style={{ opacity: done ? 0.7 : 1 }}>{s}…</span>
              </div>
            );
          })}
        </div>
      )}

      {error && !loading && (
        <div style={{ fontSize: 12, color: '#b4442e', fontFamily: 'ui-monospace, monospace' }}>{error}</div>
      )}
    </div>
  );
}
