import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme, ThemeName } from '../theme';

interface Props {
  th: Theme;
  lang: Lang;
  setLang: (l: Lang) => void;
  theme: ThemeName;
  setTheme: (t: ThemeName) => void;
  onSignInClick?: () => void;
}

// Below this width the brand block (logo + lang toggle + theme + sign-in)
// no longer fits side-by-side at full size, so we shrink paddings, fonts,
// and control sizes so "Lentochka" stops getting overlapped by the toggle.
const COMPACT_BREAKPOINT = 640;

function useIsCompact(threshold: number): boolean {
  const [compact, setCompact] = useState(() =>
    typeof window === 'undefined' ? false : window.innerWidth < threshold
  );
  useEffect(() => {
    const onResize = () => setCompact(window.innerWidth < threshold);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [threshold]);
  return compact;
}

export function TopBar({ th, lang, setLang, theme, setTheme, onSignInClick }: Props) {
  const { user, logout, isTelegram } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const compact = useIsCompact(COMPACT_BREAKPOINT);

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [menuOpen]);

  const initial = (user?.name || user?.email || '?').trim().charAt(0).toUpperCase();

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: compact ? '12px 12px' : '18px 28px',
      gap: 8,
      borderBottom: `1px solid ${th.line}`,
      background: th.bg,
      position: 'sticky', top: 0, zIndex: 5,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flexShrink: 1 }}>
        <div style={{ width: compact ? 28 : 32, height: compact ? 28 : 32, borderRadius: 7, overflow: 'hidden', flexShrink: 0, boxShadow: '0 2px 6px rgba(0,0,0,0.15)' }}>
          <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
            <rect width="64" height="64" rx="14" fill="#3d2442" />
            <rect x="10" y="18" width="22" height="32" rx="2" fill="#f5e6b8" fillOpacity="0.16" />
            <rect x="14" y="16" width="22" height="34" rx="2" fill="#f5e6b8" fillOpacity="0.28" />
            <g transform="rotate(8 34 32)">
              <path d="M22 14h16l8 8v26a2 2 0 0 1-2 2H22a2 2 0 0 1-2-2V16a2 2 0 0 1 2-2z" fill="#f5e6b8" />
              <path d="M38 14l8 8h-6a2 2 0 0 1-2-2v-6z" fill="#e4b15c" />
              <path d="M29 30 L40 36.5 L29 43 Z" fill="#2a1830" />
            </g>
          </svg>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1, minWidth: 0 }}>
          <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: compact ? 15 : 19, color: th.ink, letterSpacing: -0.3, whiteSpace: 'nowrap' }}>
            {T.appName[lang]}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: compact ? 6 : 12, flexShrink: 0 }}>
        <div style={{ display: 'flex', background: th.chipBg, borderRadius: 999, padding: 2, fontSize: 11, fontWeight: 600 }}>
          {(['ru', 'en'] as Lang[]).map((l) => (
            <button key={l} onClick={() => setLang(l)} style={{
              border: 'none', borderRadius: 999, padding: compact ? '5px 9px' : '6px 12px', cursor: 'pointer',
              background: lang === l ? th.plum : 'transparent',
              color: lang === l ? th.plumInk : th.ink2,
              fontWeight: 600, letterSpacing: 0.3, textTransform: 'uppercase', fontSize: compact ? 10.5 : 12,
            }}>{l}</button>
          ))}
        </div>
        <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          title={theme === 'light' ? 'Dark' : 'Light'}
          style={{
            border: `1px solid ${th.line}`, background: 'transparent', color: th.ink2,
            width: compact ? 30 : 36, height: compact ? 30 : 36, borderRadius: 999, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
          }}>
          {theme === 'light' ? '☾' : '☀'}
        </button>
        {!user && !isTelegram && onSignInClick && (
          <button
            onClick={onSignInClick}
            style={{
              border: `1px solid ${th.line}`, background: 'transparent', color: th.ink,
              padding: compact ? '6px 12px' : '7px 16px', borderRadius: 999, cursor: 'pointer',
              fontSize: compact ? 12 : 13, fontWeight: 600, letterSpacing: 0.2,
              whiteSpace: 'nowrap',
            }}
          >{T.signIn[lang]}</button>
        )}
        {user && (
          <div ref={wrapRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setMenuOpen((v) => !v)}
              title={user.email}
              style={{
                border: `1px solid ${th.line}`, background: th.chipBg, color: th.ink,
                width: compact ? 30 : 36, height: compact ? 30 : 36, borderRadius: '50%',
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: compact ? 12 : 14, fontWeight: 700, overflow: 'hidden', padding: 0,
              }}
            >
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                initial
              )}
            </button>
            {menuOpen && (
              <div style={{
                position: 'absolute', right: 0, top: 'calc(100% + 8px)',
                minWidth: 220, background: th.surface,
                border: `1px solid ${th.line}`, borderRadius: 12,
                boxShadow: th.shadow, padding: 10, zIndex: 20,
              }}>
                <div style={{ padding: '4px 8px 8px 8px', borderBottom: `1px solid ${th.line}`, marginBottom: 6 }}>
                  {user.name && (
                    <div style={{ fontSize: 13, fontWeight: 600, color: th.ink, marginBottom: 2 }}>{user.name}</div>
                  )}
                  <div style={{ fontSize: 12, color: th.ink3, wordBreak: 'break-all' }}>{user.email}</div>
                </div>
                <button
                  onClick={() => { setMenuOpen(false); logout(); }}
                  style={{
                    width: '100%', textAlign: 'left', padding: '8px 8px',
                    background: 'transparent', border: 'none', color: th.ink,
                    borderRadius: 8, cursor: 'pointer', fontSize: 13,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = th.chipBg)}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  {T.logout[lang]}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
