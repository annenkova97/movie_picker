import { useAuth } from '../auth';
import { useSettings } from '../settings';
import { T, type Lang } from '../i18n';
import type { ThemeName } from '../theme';

interface Props {
  onClose: () => void;
  /** Opens the existing ShareModal (lives higher up in the tree). */
  onOpenShare: () => void;
  /** Opens the auth screen for a signed-out guest. */
  onOpenAuth: () => void;
}

/**
 * Wine-deep settings sheet reached from the header gear. Consolidates the
 * cross-cutting preferences (language, theme), account actions, and the
 * "share my list" entry that used to be the gear's only behaviour.
 */
export function SettingsSheet({ onClose, onOpenShare, onOpenAuth }: Props) {
  const { lang, setLang, theme, setTheme } = useSettings();
  const { user, logout, isTelegram } = useAuth();

  return (
    <div className="lt-screen st-overlay" onClick={onClose}>
      <div className="st-sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="st-handle" aria-hidden />
        <div className="st-head">
          <h2 className="st-title">{T.settingsTitle[lang]}</h2>
          <button className="st-close" onClick={onClose} aria-label={T.settingsClose[lang]}>×</button>
        </div>

        {/* Language */}
        <div className="st-row">
          <span className="st-label">{T.settingsLanguage[lang]}</span>
          <div className="st-seg">
            {(['ru', 'en'] as Lang[]).map((l) => (
              <button
                key={l}
                className={`st-seg__btn${lang === l ? ' is-active' : ''}`}
                onClick={() => setLang(l)}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Theme */}
        <div className="st-row">
          <span className="st-label">{T.settingsTheme[lang]}</span>
          <div className="st-seg">
            {(['light', 'dark'] as ThemeName[]).map((t) => (
              <button
                key={t}
                className={`st-seg__btn${theme === t ? ' is-active' : ''}`}
                onClick={() => setTheme(t)}
              >
                {t === 'light' ? T.settingsThemeLight[lang] : T.settingsThemeDark[lang]}
              </button>
            ))}
          </div>
        </div>

        {/* Account */}
        <div className="st-row st-row--stack">
          <span className="st-label">{T.settingsAccount[lang]}</span>
          {user ? (
            <div className="st-account">
              <div className="st-account__name">{user.name || user.email}</div>
              {!isTelegram && (
                <button className="st-account__action" onClick={() => { logout(); onClose(); }}>
                  {T.logout[lang]}
                </button>
              )}
            </div>
          ) : (
            <div className="st-account">
              <div className="st-account__name st-account__name--muted">{T.settingsGuest[lang]}</div>
              <button className="st-account__action" onClick={() => { onClose(); onOpenAuth(); }}>
                {T.signIn[lang]}
              </button>
            </div>
          )}
        </div>

        {/* Share */}
        <button className="st-share" onClick={() => { onClose(); onOpenShare(); }}>
          <span aria-hidden>🔗</span> {T.settingsShareList[lang]}
        </button>

        <style>{styles}</style>
      </div>
    </div>
  );
}

const styles = `
.st-overlay {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(20, 10, 18, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.st-sheet {
  width: 100%;
  max-width: 430px;
  background: var(--color-wine);
  border: 1px solid var(--wine-light-border);
  border-bottom: none;
  border-radius: 24px 24px 0 0;
  padding: 10px 20px calc(28px + env(safe-area-inset-bottom, 0px));
  box-shadow: 0 -8px 40px rgba(0, 0, 0, 0.45);
  animation: st-rise 0.22s ease both;
}
@keyframes st-rise { from { transform: translateY(20px); opacity: 0; } to { transform: none; opacity: 1; } }
.st-handle {
  width: 40px; height: 4px; border-radius: 999px;
  background: var(--wine-light-border);
  margin: 4px auto 14px;
}
.st-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.st-title {
  font-family: var(--font-display);
  font-weight: 700; font-size: 22px; letter-spacing: -0.3px;
  color: var(--color-cream); margin: 0;
}
.st-close {
  border: none; background: transparent; color: var(--cream-60);
  font-size: 26px; line-height: 1; cursor: pointer; padding: 0 4px;
}
.st-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 16px 0;
  border-bottom: 1px solid var(--wine-light-border);
}
.st-row--stack { align-items: flex-start; }
.st-label {
  font-family: var(--font-body); font-weight: 600; font-size: 15px;
  color: var(--color-cream);
}
.st-seg {
  display: inline-flex; background: var(--color-wine-deep);
  border: 1px solid var(--wine-light-border); border-radius: 999px; padding: 3px;
}
.st-seg__btn {
  border: none; background: transparent; color: var(--cream-60);
  font-family: var(--font-body); font-weight: 600; font-size: 13px;
  padding: 6px 14px; border-radius: 999px; cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.st-seg__btn.is-active {
  background: var(--gold-tint-strong); color: var(--color-cream);
}
.st-account {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  justify-content: flex-end;
}
.st-account__name {
  font-family: var(--font-body); font-size: 14px; color: var(--cream-85);
  max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.st-account__name--muted { color: var(--cream-60); }
.st-account__action {
  border: 1px solid var(--wine-light-border); background: transparent;
  color: var(--color-gold); font-family: var(--font-body); font-weight: 600;
  font-size: 13px; padding: 7px 14px; border-radius: 999px; cursor: pointer;
}
.st-account__action:hover { border-color: var(--gold-border); }
.st-share {
  width: 100%; margin-top: 20px; height: 48px; border-radius: 14px;
  border: 1px solid var(--gold-border); background: var(--gold-tint-strong);
  color: var(--color-cream); font-family: var(--font-body); font-weight: 600;
  font-size: 15px; cursor: pointer; display: inline-flex; align-items: center;
  justify-content: center; gap: 8px;
}
.st-share:hover { background: var(--gold-tint-medium); }
`;
