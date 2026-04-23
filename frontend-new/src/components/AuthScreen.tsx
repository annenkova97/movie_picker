import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../auth';
import type { Lang } from '../i18n';
import type { Theme } from '../theme';

const L = {
  titleLogin:    { ru: 'Войти в Ленточку',       en: 'Sign in to Lentochka' },
  titleRegister: { ru: 'Создать аккаунт',          en: 'Create an account' },
  emailPh:       { ru: 'Email',                    en: 'Email' },
  namePh:        { ru: 'Как к вам обращаться',     en: 'Your name' },
  passwordPh:    { ru: 'Пароль (от 6 символов)',   en: 'Password (6+ chars)' },
  loginBtn:      { ru: 'Войти',                    en: 'Sign in' },
  registerBtn:   { ru: 'Зарегистрироваться',       en: 'Create account' },
  switchToReg:   { ru: 'Нет аккаунта? Создать',    en: 'No account? Sign up' },
  switchToLog:   { ru: 'Уже есть аккаунт? Войти',  en: 'Have an account? Sign in' },
  or:            { ru: 'или',                       en: 'or' },
  googleHint:    { ru: 'Войти через Google',       en: 'Continue with Google' },
  googleNotSet:  { ru: 'Google вход пока не настроен',
                   en: 'Google sign-in is not configured yet' },
  subtitle:      { ru: 'Личный кинодневник. Сохраняй фильмы и получай рекомендации.',
                   en: 'Your personal film diary. Save movies, get recommendations.' },
} as const;

interface Props {
  th: Theme;
  lang: Lang;
}

export function AuthScreen({ th, lang }: Props) {
  const { login, register, googleLogin } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined) || '';

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setBusy(true);
    try {
      if (mode === 'login') await login(email.trim(), password);
      else await register(email.trim(), password, name.trim() || undefined);
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
    <div style={{
      minHeight: '100vh', background: th.bg, color: th.ink,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    }}>
      <div style={{
        width: '100%', maxWidth: 380, background: th.surface,
        border: `1px solid ${th.line}`, borderRadius: 18,
        padding: '28px 26px', boxShadow: th.shadow,
      }}>
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
              {mode === 'login' ? L.titleLogin[lang] : L.titleRegister[lang]}
            </div>
            <div style={{ fontSize: 12, color: th.ink3, marginTop: 3 }}>{L.subtitle[lang]}</div>
          </div>
        </div>

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {mode === 'register' && (
            <input
              type="text"
              placeholder={L.namePh[lang]}
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={inputStyle}
              autoComplete="name"
            />
          )}
          <input
            type="email"
            placeholder={L.emailPh[lang]}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={inputStyle}
            autoComplete="email"
          />
          <input
            type="password"
            placeholder={L.passwordPh[lang]}
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
            {mode === 'login' ? L.loginBtn[lang] : L.registerBtn[lang]}
          </button>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '18px 0 12px' }}>
          <div style={{ flex: 1, height: 1, background: th.line }} />
          <div style={{ fontSize: 11, color: th.ink3, textTransform: 'uppercase', letterSpacing: 0.5 }}>{L.or[lang]}</div>
          <div style={{ flex: 1, height: 1, background: th.line }} />
        </div>

        {googleClientId ? (
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <GoogleLogin
              onSuccess={(res) => { if (res.credential) onGoogle(res.credential); }}
              onError={() => setErr('Google sign-in failed')}
              theme={th.name === 'dark' ? 'filled_black' : 'outline'}
              shape="pill"
              text={mode === 'login' ? 'signin_with' : 'signup_with'}
            />
          </div>
        ) : (
          <div style={{ fontSize: 12, color: th.ink3, textAlign: 'center', padding: '4px 0' }}>
            {L.googleNotSet[lang]}
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
          {mode === 'login' ? L.switchToReg[lang] : L.switchToLog[lang]}
        </button>
      </div>
    </div>
  );
}
