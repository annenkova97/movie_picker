import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

export interface AuthUser {
  id: number;
  email: string;
  name: string | null;
  avatar_url: string | null;
  created_at: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  loading: boolean;
  // true когда страница открыта внутри Telegram (Mini App) — фронт прячет
  // экран логина, потому что мы умеем войти автоматически по initData.
  isTelegram: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  googleLogin: (idToken: string) => Promise<void>;
  logout: () => void;
}

function getTelegramInitData(): string | null {
  // Скрипт telegram-web-app.js, подгруженный в index.html, выставляет
  // window.Telegram.WebApp.initData непустой строкой только когда страница
  // реально открыта из Telegram (бот → Mini App).
  const tg = (window as { Telegram?: { WebApp?: { initData?: string; ready?: () => void; expand?: () => void } } }).Telegram?.WebApp;
  if (!tg || !tg.initData) return null;
  // Сигналим Telegram, что приложение готово, и раскрываем на всю высоту.
  try { tg.ready?.(); tg.expand?.(); } catch {}
  return tg.initData;
}

const AuthContext = createContext<AuthState | null>(null);

const TOKEN_KEY = 'lentochka.token';

let currentToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function getToken(): string | null {
  return currentToken;
}

function setCurrentToken(t: string | null) {
  currentToken = t;
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {}
}

export function registerUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

export function handleUnauthorized() {
  setCurrentToken(null);
  onUnauthorized?.();
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data?.detail) msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

interface AuthResponse { token: string; user: AuthUser }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  });
  const [user, setUser] = useState<AuthUser | null>(null);
  // Внутри Telegram даже без сохранённого токена покажем спиннер, пока
  // не дойдёт auto-login по initData — иначе мелькнёт экран регистрации.
  const isTelegram = typeof window !== 'undefined' && !!getTelegramInitData();
  const [loading, setLoading] = useState<boolean>(!!token || isTelegram);

  // keep the module-level token in sync so api.ts can read it
  useEffect(() => { currentToken = token; }, [token]);

  const clear = useCallback(() => {
    setCurrentToken(null);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    registerUnauthorizedHandler(clear);
  }, [clear]);

  const applyAuth = useCallback((res: AuthResponse) => {
    setCurrentToken(res.token);
    setToken(res.token);
    setUser(res.user);
  }, []);

  // Initial auth — пробуем сначала Telegram WebApp (если открыты из Telegram),
  // потом сохранённый токен из localStorage. Запускается один раз на маунт.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const tgInitData = getTelegramInitData();
      if (tgInitData) {
        try {
          const res = await postJson<AuthResponse>('/auth/telegram-webapp', { init_data: tgInitData });
          if (!cancelled) {
            applyAuth(res);
            setLoading(false);
          }
          return;
        } catch (e) {
          // initData протух или подпись битая — упадём в обычный flow ниже.
          console.warn('[auth] Telegram WebApp login failed:', e);
        }
      }
      // Hydrate /auth/me if we have a token from localStorage
      const storedToken = currentToken;
      if (!storedToken) {
        if (!cancelled) setLoading(false);
        return;
      }
      try {
        const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${storedToken}` } });
        if (!res.ok) throw new Error(String(res.status));
        const data: AuthUser = await res.json();
        if (!cancelled) setUser(data);
      } catch {
        if (!cancelled) clear();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // Только один раз на маунт — повторные re-runs не нужны.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await postJson<AuthResponse>('/auth/login', { email, password });
    applyAuth(res);
  }, [applyAuth]);

  const register = useCallback(async (email: string, password: string, name?: string) => {
    const res = await postJson<AuthResponse>('/auth/register', { email, password, name });
    applyAuth(res);
  }, [applyAuth]);

  const googleLogin = useCallback(async (idToken: string) => {
    const res = await postJson<AuthResponse>('/auth/google', { id_token: idToken });
    applyAuth(res);
  }, [applyAuth]);

  const logout = useCallback(() => { clear(); }, [clear]);

  const value = useMemo<AuthState>(() => ({
    token, user, loading, isTelegram, login, register, googleLogin, logout,
  }), [token, user, loading, isTelegram, login, register, googleLogin, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
