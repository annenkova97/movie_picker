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
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  googleLogin: (idToken: string) => Promise<void>;
  logout: () => void;
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
  const [loading, setLoading] = useState<boolean>(!!token);

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

  // hydrate /auth/me on mount if we have a token
  useEffect(() => {
    if (!token) { setLoading(false); return; }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
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
  }, [token, clear]);

  const applyAuth = useCallback((res: AuthResponse) => {
    setCurrentToken(res.token);
    setToken(res.token);
    setUser(res.user);
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
    token, user, loading, login, register, googleLogin, logout,
  }), [token, user, loading, login, register, googleLogin, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
