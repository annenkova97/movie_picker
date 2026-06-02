import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { Lang } from './i18n';
import type { ThemeName } from './theme';

const LANG_KEY = 'lentochka.lang';
const THEME_KEY = 'lentochka.theme';

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
  theme: ThemeName;
  setTheme: (t: ThemeName) => void;
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
 * Owns the two cross-cutting UI preferences (language + theme), persists them
 * to localStorage, and mirrors the active theme onto `<html data-theme>` so the
 * CSS-variable palette in theme.css can switch. Mirrors the AuthProvider shape.
 */
export function SettingsProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => readStored<Lang>(LANG_KEY, detectDefaultLang()));
  // Default to the dark wine palette — the brand look the app ships with today.
  const [theme, setTheme] = useState<ThemeName>(() => readStored<ThemeName>(THEME_KEY, 'dark'));

  useEffect(() => {
    try {
      localStorage.setItem(LANG_KEY, lang);
    } catch {}
  }, [lang]);

  useEffect(() => {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {}
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const value: SettingsState = { lang, setLang, theme, setTheme };
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): SettingsState {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used inside <SettingsProvider>');
  return ctx;
}
