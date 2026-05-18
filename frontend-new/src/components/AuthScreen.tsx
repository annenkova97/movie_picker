import { useCallback, useEffect, useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../auth';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import { TelegramLoginButton } from './TelegramLoginButton';
import type { TelegramWidgetUser } from './TelegramLoginButton';

interface Props {
  th: Theme;
  lang: Lang;
  initialMode?: 'login' | 'register';
  onClose?: () => void;
}

/**
 * Sign in / register screen.
 *
 * Renders as a full-screen overlay over the app — guests can dismiss it
 * via the close button or by pressing Escape. When `onClose` is omitted
 * the close affordance is hidden (used during forced re-auth flows, if any).
 */
export function AuthScreen({ th, lang, initialMode = 'login', onClose }: Props) {
  const { login, register, googleLogin, telegramWidgetLogin } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [telegramBot, setTelegramBot] = useState<string | null>(null);

  const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined) || '';

  // Один раз дёргаем username бота — фронт сам узнаёт его, не нужно дублировать в env.
  useEffect(() => {
    let cancelled = false;
    fetch('/auth/telegram-bot-info')
      .then((r) => r.ok ? r.json() : null)
      .then((data: { username?: string; enabled?: boolean } | null) => {
        if (!cancelled && data?.enabled && data.username) {
          setTelegramBot(data.username);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const onTelegramAuth = useCallback(async (user: TelegramWidgetUser) => {
    setErr(null); setBusy(true);
    try {
      await telegramWidgetLogin(user as unknown as Record<string, unknown>);
      onClose?.();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  }, [telegramWidgetLogin, onClose]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setBusy(true);
    try {
      if (mode === 'login') await login(email.trim(), password);
      else await register(email.trim(), password, name.trim() || undefined);
      onClose?.();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  };

  const onGoogle = async (idToken: string) => {
    setErr(null); setBusy(true);
    try {
      await googleLogin(idToken);
      onClose?.();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '12px 14px', fontSize: 14,
    border: `1px solid ${th.line}`, borderRadius: 10,
    background: th.surface, color: th.ink, boxSizing: 'border-box',
    outline: 'none',
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={() => onClose?.()}
      style={{
        position: 'fixed', inset: 0, zIndex: 40,
        minHeight: '100vh', background: 'rgba(30,15,25,0.55)',
        backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
        color: th.ink,
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%', maxWidth: 380, background: th.surface,
          border: `1px solid ${th.line}`, borderRadius: 18,
          padding: '28px 26px', boxShadow: th.shadow,
          position: 'relative',
        }}
      >
        {onClose && (
          <button
            onClick={onClose}
            aria-label="close"
            style={{
              position: 'absolute', top: 10, right: 12,
              border: 'none', background: 'transparent', color: th.ink3, fontSize: 22,
              cursor: 'pointer', padding: 0, width: 28, height: 28, lineHeight: 1,
            }}
          >×</button>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
          <div style={{ width: 36, height: 36, borderRadius: 8, overflow: 'hidden', boxShadow: '0 2px 6px rgba(0,0,0,0.15)' }}>
            <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
              <rect width="64" height="64" rx="14" fill="#3d2442" />
              <g transform="rotate(8 34 32)">
                <path d="M22 14h16l8 8v26a2 2 0 0 1-2 2H22a2 2 0 0 1-2-2V16a2 2 0 0 1 2-2z" fill="#f5e6b8" />
                <path d="M38 14l8 8h-6a2 2 0 0 1-2-2v-6z" fill="#e4b15c" />
                <path d="M29 30 L40 36.5 L29 43 Z" fill="#2a1830" />
              </g>
            </svg>
          </div>
          <div>
            <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontWeight: 700, fontSize: 20, letterSpacing: -0.3 }}>
              {mode === 'login' ? T.authTitleLogin[lang] : T.authTitleRegister[lang]}
            </div>
            <div style={{ fontSize: 12, color: th.ink3, marginTop: 3 }}>{T.authSubtitle[lang]}</div>
          </div>
        </div>

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {mode === 'register' && (
            <input
              type="text"
              placeholder={T.authNamePh[lang]}
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={inputStyle}
              autoComplete="name"
            />
          )}
          <input
            type="email"
            placeholder={T.authEmailPh[lang]}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={inputStyle}
            autoComplete="email"
          />
          <input
            type="password"
            placeholder={T.authPasswordPh[lang]}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            style={inputStyle}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          />
          {err && (
            <div style={{
              background: 'rgba(200,40,40,0.08)', color: '#b22222',
              border: '1px solid rgba(200,40,40,0.25)', borderRadius: 10,
              padding: '9px 12px', fontSize: 12.5,
            }}>{err}</div>
          )}
          <button
            type="submit"
            disabled={busy}
            style={{
              marginTop: 4, padding: '12px 14px', border: 'none', cursor: busy ? 'wait' : 'pointer',
              background: th.plum, color: th.plumInk, borderRadius: 999,
              fontWeight: 600, fontSize: 14, letterSpacing: 0.2,
              boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
              opacity: busy ? 0.7 : 1,
            }}
          >
            {mode === 'login' ? T.authLoginBtn[lang] : T.authRegisterBtn[lang]}
          </button>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '18px 0 12px' }}>
          <div style={{ flex: 1, height: 1, background: th.line }} />
          <div style={{ fontSize: 11, color: th.ink3, textTransform: 'uppercase', letterSpacing: 0.5 }}>{T.authOr[lang]}</div>
          <div style={{ flex: 1, height: 1, background: th.line }} />
        </div>

        {telegramBot && (
          <div style={{ marginBottom: 10 }}>
            <TelegramLoginButton
              botUsername={telegramBot}
              onAuth={onTelegramAuth}
            />
          </div>
        )}

        {googleClientId ? (
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <GoogleLogin
              onSuccess={(res) => { if (res.credential) onGoogle(res.credential); }}
              onError={() => setErr(T.authGoogleFail[lang])}
              theme={th.name === 'dark' ? 'filled_black' : 'outline'}
              shape="pill"
              text={mode === 'login' ? 'signin_with' : 'signup_with'}
            />
          </div>
        ) : (
          <div style={{ fontSize: 12, color: th.ink3, textAlign: 'center', padding: '4px 0' }}>
            {T.authGoogleNotSet[lang]}
          </div>
        )}

        <button
          type="button"
          onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setErr(null); }}
          style={{
            marginTop: 18, width: '100%', padding: '8px 0',
            background: 'transparent', border: 'none', color: th.ink2,
            fontSize: 13, cursor: 'pointer', textDecoration: 'underline',
          }}
        >
          {mode === 'login' ? T.authSwitchToReg[lang] : T.authSwitchToLog[lang]}
        </button>
      </div>
    </div>
  );
}
