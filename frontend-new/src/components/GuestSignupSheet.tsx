import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';

interface Props {
  th: Theme;
  lang: Lang;
  onCreate: () => void;
  onSignIn: () => void;
  onSkip: () => void;
}

/**
 * Bottom sheet shown after a guest's first save.
 * Non-blocking: dismissable via X or "Not now". Sticky once dismissed (see
 * useGuestSignupPrompt for the storage flag).
 */
export function GuestSignupSheet({ th, lang, onCreate, onSignIn, onSkip }: Props) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onSkip}
      style={{
        position: 'fixed', inset: 0, zIndex: 25,
        background: 'rgba(30,15,25,0.55)',
        backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
        padding: '20px 16px 20px',
        animation: 'gss-fadein 0.2s ease both',
      }}
    >
      <style>{`
        @keyframes gss-fadein { from { opacity: 0 } to { opacity: 1 } }
        @keyframes gss-slidein { from { transform: translateY(20px); opacity: 0 } to { transform: none; opacity: 1 } }
      `}</style>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: th.surface, borderRadius: 20, padding: 22,
          width: '100%', maxWidth: 460,
          boxShadow: th.shadowLg, border: `1px solid ${th.line}`,
          display: 'flex', flexDirection: 'column', gap: 14,
          animation: 'gss-slidein 0.22s ease both',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 11, fontFamily: 'ui-monospace,monospace', color: th.ink3, textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 6 }}>
              ✦ {T.appName[lang]}
            </div>
            <div style={{ fontFamily: "'Fraunces', serif", fontWeight: 700, fontSize: 22, color: th.ink, letterSpacing: -0.3, lineHeight: 1.15 }}>
              {T.guestSheetTitle[lang]}
            </div>
            <div style={{ fontSize: 13.5, color: th.ink2, lineHeight: 1.45, marginTop: 8 }}>
              {T.guestSheetBody[lang]}
            </div>
          </div>
          <button
            onClick={onSkip}
            aria-label="close"
            style={{
              border: 'none', background: 'transparent', color: th.ink3, fontSize: 22,
              cursor: 'pointer', padding: 0, width: 28, height: 28, lineHeight: 1, flexShrink: 0,
            }}
          >×</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
          <button
            onClick={onCreate}
            style={{
              border: 'none', background: th.plum, color: th.plumInk,
              padding: '12px 16px', borderRadius: 12, cursor: 'pointer',
              fontSize: 14, fontWeight: 600, letterSpacing: 0.2,
            }}
          >{T.guestSheetCreate[lang]}</button>
          <button
            onClick={onSignIn}
            style={{
              border: `1px solid ${th.line}`, background: 'transparent', color: th.ink,
              padding: '11px 16px', borderRadius: 12, cursor: 'pointer',
              fontSize: 14, fontWeight: 500,
            }}
          >{T.guestSheetSignIn[lang]}</button>
          <button
            onClick={onSkip}
            style={{
              border: 'none', background: 'transparent', color: th.ink3,
              padding: '8px 0 0', cursor: 'pointer',
              fontSize: 12.5, fontWeight: 500,
            }}
          >{T.guestSheetSkip[lang]}</button>
        </div>
      </div>
    </div>
  );
}
