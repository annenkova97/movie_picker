import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme, ThemeName } from '../theme';

interface Props {
  th: Theme;
  lang: Lang;
  setLang: (l: Lang) => void;
  theme: ThemeName;
  setTheme: (t: ThemeName) => void;
  onAdd: () => void;
  compact?: boolean;
}

export function TopBar({ th, lang, setLang, theme, setTheme, onAdd, compact = false }: Props) {
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
            </g>
            <path d="M29 30 L40 36.5 L29 43 Z" fill="#2a1830" />
          </svg>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1, minWidth: 0 }}>
          <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontWeight: 700, fontSize: compact ? 15 : 19, color: th.ink, letterSpacing: -0.3, whiteSpace: 'nowrap' }}>
            {T.appName[lang]}
          </div>
          {!compact && <div style={{ fontSize: 11, color: th.ink3, marginTop: 3, fontStyle: 'italic' }}>{T.tagline[lang]}</div>}
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
        <button onClick={onAdd} style={{
          border: 'none', background: th.plum, color: th.plumInk,
          padding: compact ? '7px 11px' : '10px 18px', borderRadius: 999, cursor: 'pointer',
          fontSize: compact ? 12 : 13, fontWeight: 600, letterSpacing: 0.2, whiteSpace: 'nowrap',
          boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
        }}>
          {compact ? (lang === 'ru' ? '+ Добавить' : '+ Add') : T.addMovie[lang]}
        </button>
      </div>
    </div>
  );
}
