import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { Lang } from './i18n';

const LANG_KEY = 'lentochka.lang';
const REGION_KEY = 'lentochka.region';
const SERVICES_KEY = 'lentochka.services';

// Default streaming region. The owner is in Russia; non-RU users can switch in
// the settings sheet. (TMDb country code.)
const DEFAULT_REGION = 'RU';

function readServices(): number[] {
  try {
    const raw = localStorage.getItem(SERVICES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x): x is number => typeof x === 'number') : [];
  } catch {
    return [];
  }
}

/**
 * Device language → default UI language.
 *
 * Russian only when the device locale is Russian; everyone else defaults to
 * English so a non-Russian visitor isn't dropped onto an unfamiliar language.
 * Inside Telegram we trust the Mini App `language_code`; on the web we fall
 * back to `navigator.language`. Used ONLY when the user hasn't picked a
 * language yet (no stored preference).
 */
export function detectDefaultLang(): Lang {
  try {
    const tgLang = (
      window as {
        Telegram?: { WebApp?: { initDataUnsafe?: { user?: { language_code?: string } } } };
      }
    ).Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
    const code = (tgLang || (typeof navigator !== 'undefined' ? navigator.language : '') || '').toLowerCase();
    return code.startsWith('ru') ? 'ru' : 'en';
  } catch {
    return 'en';
  }
}

interface SettingsState {
  lang: Lang;
  setLang: (l: Lang) => void;
  /** Streaming region (TMDb country code) for availability lookups. */
  region: string;
  setRegion: (r: string) => void;
  /** TMDb provider ids the user is subscribed to (for the availability filter). */
  services: number[];
  setServices: (s: number[]) => void;
}

const SettingsContext = createContext<SettingsState | null>(null);

function readStored<T extends string>(key: string, fallback: T): T {
  try {
    return (localStorage.getItem(key) as T) || fallback;
  } catch {
    return fallback;
  }
}

/**
 * Owns the UI language preference and persists it. (Theme was removed — the app
 * is dark-only for now.) Mirrors the AuthProvider shape.
 */
export function SettingsProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => readStored<Lang>(LANG_KEY, detectDefaultLang()));
  const [region, setRegion] = useState<string>(() => readStored(REGION_KEY, DEFAULT_REGION));
  const [services, setServices] = useState<number[]>(() => readServices());

  useEffect(() => {
    try {
      localStorage.setItem(LANG_KEY, lang);
    } catch {}
  }, [lang]);

  useEffect(() => {
    try {
      localStorage.setItem(REGION_KEY, region);
    } catch {}
  }, [region]);

  useEffect(() => {
    try {
      localStorage.setItem(SERVICES_KEY, JSON.stringify(services));
    } catch {}
  }, [services]);

  const value: SettingsState = { lang, setLang, region, setRegion, services, setServices };
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): SettingsState {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used inside <SettingsProvider>');
  return ctx;
}
