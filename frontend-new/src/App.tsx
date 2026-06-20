import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from './auth';
import { useGuestSignupPrompt, useLibrary } from './hooks/useLibrary';
import { migrateGuestLibrary } from './library';
import { migrateGuestBooks } from './bookLibrary';
import { AuthScreen } from './components/AuthScreen';
import { GuestSignupSheet } from './components/GuestSignupSheet';
import { ShareModal } from './components/ShareModal';
import { SharedListView } from './components/SharedListView';
import { PrivacyPage } from './components/PrivacyPage';
import { TonightMoodFilters } from './components/tonight/TonightMoodFilters';
import { TonightResults, SAMPLE_FILMS } from './components/tonight/TonightResults';
import { WatchlistMain, SAMPLE_SAVED, SAMPLE_RECS } from './components/watchlist/WatchlistMain';
import { WatchlistEmpty } from './components/watchlist/WatchlistEmpty';
import { LentochkaApp } from './LentochkaApp';
import { SettingsProvider, useSettings } from './settings';
import { track } from './analytics';
import type { Lang } from './i18n';
import { T } from './i18n';
import { THEMES, type Theme } from './theme';
import { toUiMovie, type UiMovie } from './types';

function readShareSlug(): string | null {
  // No router yet — keep it dead simple. Path /s/<slug> renders the share view.
  const path = window.location.pathname;
  const match = path.match(/^\/s\/([\w-]+)\/?$/);
  return match ? match[1] : null;
}

function readDebugScreen(): string | null {
  // Standalone preview for new design screens: ?screen=tonight-pick
  const params = new URLSearchParams(window.location.search);
  return params.get('screen');
}

export default function App() {
  return (
    <SettingsProvider>
      <AppShell />
    </SettingsProvider>
  );
}

function AppShell() {
  const { lang } = useSettings();
  // App is dark-only now; legacy modal components still take a theme object.
  const th = THEMES.dark;
  const auth = useAuth();
  const shareSlug = readShareSlug();

  // Body chrome (bg, color, font-family) lives in design/theme.css → global.css.
  // No JS override needed; the new wine-deep palette wins by default.

  if (auth.loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: th.ink3, fontSize: 13 }}>
        {T.authLoading[lang]}
      </div>
    );
  }

  if (window.location.pathname.replace(/\/$/, '') === '/privacy') {
    return <PrivacyPage />;
  }

  if (shareSlug) {
    return <SharedListView th={th} lang={lang} slug={shareSlug} />;
  }

  const debugScreen = readDebugScreen();
  if (debugScreen === 'tonight-pick') {
    return (
      <TonightMoodFilters
        open
        onClose={() => { window.location.search = ''; }}
        onSubmit={(p) => { console.log('[tonight-pick:submit]', p); }}
      />
    );
  }
  if (debugScreen === 'tonight-results') {
    return (
      <TonightResults
        open
        mood="🌧 Уютно"
        duration="2 ч"
        films={SAMPLE_FILMS}
        onClose={() => { window.location.search = ''; }}
        onRefine={() => console.log('[tonight-results:refine]')}
        onLaunch={(f) => console.log('[tonight-results:launch]', f.title)}
      />
    );
  }
  if (debugScreen === 'watchlist') {
    return (
      <WatchlistMain
        userName="Настя"
        films={SAMPLE_SAVED}
        recommendations={SAMPLE_RECS}
        onOpenTonight={() => console.log('[watchlist:open-tonight]')}
        onOpenAuth={() => console.log('[watchlist:open-auth]')}
        onShare={() => console.log('[watchlist:share]')}
        onOpenSearch={() => console.log('[watchlist:open-search]')}
        onOpenBooks={() => console.log('[watchlist:open-books]')}
        onSelectFilm={(f) => console.log('[watchlist:select-film]', f.title)}
        onSelectRec={(f) => console.log('[watchlist:select-rec]', f.title)}
        onSeeAllAwards={() => console.log('[watchlist:see-all]')}
      />
    );
  }
  if (debugScreen === 'watchlist-empty') {
    return (
      <WatchlistEmpty
        userName="Настя"
        curated={SAMPLE_RECS}
        bookCount={0}
        onOpenAuth={() => console.log('[empty:open-auth]')}
        onOpenSearch={() => console.log('[empty:open-search]')}
        onOpenBooks={() => console.log('[empty:open-books]')}
        onSave={(f) => console.log('[empty:save]', f.title)}
        onSelectFilm={(f) => console.log('[empty:select]', f.title)}
      />
    );
  }

  return <AppInner th={th} lang={lang} />;
}

interface AppInnerProps {
  th: Theme;
  lang: Lang;
}

function AppInner({ th, lang }: AppInnerProps) {
  const qc = useQueryClient();
  const auth = useAuth();
  const lib = useLibrary();

  // After a successful login/register, drain any guest data the user accrued
  // before signing in. Idempotent: if there's nothing local, the call is a
  // no-op. We invalidate library cache on success so the freshly imported
  // movies appear without a manual reload.
  useEffect(() => {
    if (!auth.user) return;
    let cancelled = false;
    migrateGuestLibrary()
      .then((count) => {
        if (cancelled) return;
        if (count > 0) qc.invalidateQueries({ queryKey: ['library'] });
      })
      .catch((err) => console.warn('[migrate] guest library migration failed:', err));
    migrateGuestBooks()
      .then((count) => {
        if (cancelled) return;
        if (count > 0) qc.invalidateQueries({ queryKey: ['books'] });
      })
      .catch((err) => console.warn('[migrate] guest books migration failed:', err));
    return () => { cancelled = true; };
  }, [auth.user?.id, qc]);

  const moviesQuery = lib.list;
  const uiMovies = useMemo<UiMovie[]>(
    () => (moviesQuery.data ?? []).map(toUiMovie),
    [moviesQuery.data],
  );

  const [authMode, setAuthMode] = useState<'login' | 'register' | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const guestPrompt = useGuestSignupPrompt(uiMovies.length, lib.isGuest);

  // One app_open per load — the backbone signal for return/retention metrics.
  useEffect(() => {
    track('app_open');
  }, []);

  return (
    <>
      <LentochkaApp
        onOpenAuth={() => setAuthMode('login')}
        onOpenShare={() => { track('share_opened'); setShareOpen(true); }}
      />

      {guestPrompt.open && (
        <GuestSignupSheet
          th={th}
          lang={lang}
          onCreate={() => { guestPrompt.dismiss(); setAuthMode('register'); }}
          onSignIn={() => { guestPrompt.dismiss(); setAuthMode('login'); }}
          onSkip={() => guestPrompt.dismiss()}
        />
      )}

      {authMode && (
        <AuthScreen
          th={th}
          lang={lang}
          initialMode={authMode}
          onClose={() => setAuthMode(null)}
        />
      )}

      {shareOpen && (
        <ShareModal
          th={th}
          lang={lang}
          ownerName={auth.user?.name ?? null}
          isGuest={lib.isGuest}
          library={moviesQuery.data ?? []}
          onClose={() => setShareOpen(false)}
        />
      )}
    </>
  );
}
