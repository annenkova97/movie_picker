import { useEffect, useMemo, useState } from 'react';
import { createShare } from '../api';
import type { ApiMovie } from '../types';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';

const GUEST_NAME_KEY = 'lentochka.guestName';

interface Props {
  th: Theme;
  lang: Lang;
  /** Authenticated user display name, or null for guests. */
  ownerName: string | null;
  /** True for guest mode — we send `library` inline. */
  isGuest: boolean;
  /** Snapshot to share for guests. Backend ignores it for authed users. */
  library: ApiMovie[];
  onClose: () => void;
}

function readGuestName(): string {
  try {
    return localStorage.getItem(GUEST_NAME_KEY) || '';
  } catch {
    return '';
  }
}

function writeGuestName(name: string): void {
  try {
    if (name) localStorage.setItem(GUEST_NAME_KEY, name);
    else localStorage.removeItem(GUEST_NAME_KEY);
  } catch {}
}

function defaultListName(displayName: string, lang: Lang): string {
  if (!displayName) return T.shareNameDefaultMy[lang];
  return T.shareNameDefaultRu[lang].replace('%s', displayName);
}

export function ShareModal({ th, lang, ownerName, isGuest, library, onClose }: Props) {
  const initialOwnerName = useMemo(() => {
    if (ownerName) return ownerName;
    if (isGuest) return readGuestName();
    return '';
  }, [ownerName, isGuest]);

  // We need a name to seed the list-name field. For guests without a saved
  // name, prompt for it once before the main share form.
  const [stage, setStage] = useState<'name' | 'compose' | 'done'>(
    isGuest && !initialOwnerName ? 'name' : 'compose',
  );
  const [displayName, setDisplayName] = useState(initialOwnerName);
  const [listName, setListName] = useState(() => defaultListName(initialOwnerName, lang));
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // When the user types a name in the prompt stage, rebuild the default list
  // name from it so they don't have to retype.
  useEffect(() => {
    if (stage === 'name') return;
    setListName((prev) => {
      // Only auto-fill if the user hasn't customised yet.
      const stillDefault = prev === defaultListName('', lang)
        || prev === defaultListName(initialOwnerName, lang);
      return stillDefault ? defaultListName(displayName, lang) : prev;
    });
  }, [displayName, lang, stage, initialOwnerName]);

  const handleNameContinue = () => {
    const trimmed = displayName.trim();
    if (isGuest && trimmed) writeGuestName(trimmed);
    setListName(defaultListName(trimmed, lang));
    setStage('compose');
  };

  const handleNameSkip = () => {
    setDisplayName('');
    setListName(defaultListName('', lang));
    setStage('compose');
  };

  const handleCreate = async () => {
    setError(null);
    if (library.length === 0) {
      setError(T.shareEmptyError[lang]);
      return;
    }
    setCreating(true);
    try {
      const result = await createShare(
        listName.trim() || defaultListName(displayName, lang),
        isGuest ? library : undefined,
      );
      const url = `${window.location.origin}/s/${result.slug}`;
      setResultUrl(url);
      setStage('done');
      // Best-effort copy on creation; user can also click Copy in the next step.
      try {
        await navigator.clipboard.writeText(url);
        setCopied(true);
      } catch {}
    } catch (e: any) {
      setError(e?.message || T.shareCreateError[lang]);
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = async () => {
    if (!resultUrl) return;
    try {
      await navigator.clipboard.writeText(resultUrl);
      setCopied(true);
    } catch {
      setError('Could not access clipboard');
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(20,15,30,0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 1000, padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: th.surface, color: th.ink,
          borderRadius: 18, maxWidth: 460, width: '100%',
          padding: 24, boxShadow: th.shadow,
          fontFamily: 'inherit',
        }}
      >
        {stage === 'name' && (
          <>
            <h2 style={{ margin: '0 0 12px', fontFamily: "var(--font-display)", fontSize: 22, color: th.ink }}>
              {T.shareGuestNamePrompt[lang]}
            </h2>
            <input
              autoFocus
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder={T.shareGuestNamePh[lang]}
              style={{
                width: '100%', padding: '12px 14px', boxSizing: 'border-box',
                border: `1px solid ${th.line}`, borderRadius: 10, fontSize: 15,
                color: th.ink, background: th.bgAlt, marginBottom: 16,
                fontFamily: 'inherit',
              }}
              onKeyDown={(e) => { if (e.key === 'Enter') handleNameContinue(); }}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={handleNameSkip}
                style={btnGhost(th)}
              >{T.shareGuestNameSkip[lang]}</button>
              <button
                onClick={handleNameContinue}
                style={btnPrimary(th)}
              >{T.shareCreate[lang]}</button>
            </div>
          </>
        )}

        {stage === 'compose' && (
          <>
            <h2 style={{ margin: '0 0 6px', fontFamily: "var(--font-display)", fontSize: 22, color: th.ink }}>
              {T.shareTitle[lang]}
            </h2>
            <div style={{ fontSize: 12, color: th.ink3, marginBottom: 16, fontFamily: 'ui-monospace,monospace' }}>
              {library.length} {T.saved[lang]}
            </div>
            <label style={{ display: 'block', fontSize: 12, color: th.ink3, marginBottom: 6, fontFamily: 'ui-monospace,monospace' }}>
              {T.shareNameLabel[lang]}
            </label>
            <input
              autoFocus
              value={listName}
              onChange={(e) => setListName(e.target.value)}
              placeholder={T.shareNamePh[lang]}
              maxLength={80}
              style={{
                width: '100%', padding: '12px 14px', boxSizing: 'border-box',
                border: `1px solid ${th.line}`, borderRadius: 10, fontSize: 15,
                color: th.ink, background: th.bgAlt, marginBottom: 12,
                fontFamily: 'inherit',
              }}
              onKeyDown={(e) => { if (e.key === 'Enter' && !creating) handleCreate(); }}
            />
            {error && (
              <div style={{ fontSize: 12.5, color: '#b4442e', marginBottom: 12 }}>{error}</div>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={onClose} style={btnGhost(th)}>{T.shareCancel[lang]}</button>
              <button
                onClick={handleCreate}
                disabled={creating}
                style={{ ...btnPrimary(th), opacity: creating ? 0.7 : 1, cursor: creating ? 'wait' : 'pointer' }}
              >{T.shareCreate[lang]}</button>
            </div>
          </>
        )}

        {stage === 'done' && resultUrl && (
          <>
            <h2 style={{ margin: '0 0 16px', fontFamily: "var(--font-display)", fontSize: 22, color: th.ink }}>
              {copied ? T.shareCopied[lang] : T.shareTitle[lang]}
            </h2>
            <div style={{
              background: th.bgAlt, border: `1px solid ${th.line}`,
              padding: '12px 14px', borderRadius: 10, marginBottom: 16,
              fontFamily: 'ui-monospace,monospace', fontSize: 13,
              color: th.ink2, wordBreak: 'break-all',
            }}>
              {resultUrl}
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={onClose} style={btnGhost(th)}>{T.shareCancel[lang]}</button>
              <button onClick={handleCopy} style={btnPrimary(th)}>{T.shareCopy[lang]}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function btnPrimary(th: Theme): React.CSSProperties {
  return {
    border: 'none', background: th.plum, color: th.plumInk,
    padding: '10px 18px', borderRadius: 10, fontSize: 14, fontWeight: 600,
    cursor: 'pointer', fontFamily: 'inherit',
  };
}

function btnGhost(th: Theme): React.CSSProperties {
  return {
    border: `1px solid ${th.line}`, background: 'transparent', color: th.ink2,
    padding: '10px 16px', borderRadius: 10, fontSize: 14, fontWeight: 500,
    cursor: 'pointer', fontFamily: 'inherit',
  };
}
