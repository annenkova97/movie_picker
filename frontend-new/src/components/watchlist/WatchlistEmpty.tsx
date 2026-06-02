import { useSettings } from '../../settings';
import { T } from '../../i18n';
import type { RecFilm } from './WatchlistMain';
import { SAMPLE_RECS, LangToggle, SearchIcon } from './WatchlistMain';
import { CuratedGrid } from './CuratedGrid';

interface Props {
  userName: string;
  curated: RecFilm[];
  onOpenSettings: () => void;
  onOpenSearch: () => void;
  onOpenBooks: () => void;
  onSave: (film: RecFilm) => void;
  onSelectFilm: (film: RecFilm) => void;
}

export function WatchlistEmpty({
  userName, curated, onOpenSettings, onOpenSearch, onOpenBooks, onSave, onSelectFilm,
}: Props) {
  const { lang, setLang } = useSettings();

  return (
    <div className="lt-screen wl-screen">
      <header className="wl-header">
        <div>
          <div className="wl-greeting">{T.greetingBack[lang].replace('%s', userName)} <span aria-hidden>🎬</span></div>
          <h1 className="wl-title">{T.wlTitle[lang]}</h1>
        </div>
        <div className="wl-actions">
          <LangToggle lang={lang} setLang={setLang} />
          <button className="wl-iconbtn" onClick={onOpenSearch} aria-label={T.searchAria[lang]}>
            <SearchIcon />
          </button>
          <button className="wl-iconbtn" onClick={onOpenSettings} aria-label={T.settingsAria[lang]}>
            <SettingsIcon />
          </button>
        </div>
      </header>

      <section className="we-hero">
        <div className="we-hero__title">{T.emptyHeroTitle[lang]} <span aria-hidden>🎬</span></div>
        <div className="we-hero__sub">
          {T.emptyHeroSub[lang]}
        </div>
        <button className="we-hero__books" onClick={onOpenBooks}>
          📚 {T.booksTitle[lang]} →
        </button>
      </section>

      <section className="we-recs">
        <div className="we-recs__eyebrow">{T.wlRecsEyebrow[lang]}</div>
        <div className="we-recs__title">{T.wlRecsTitle[lang]}</div>

        <CuratedGrid
          curated={curated}
          saveLabel={T.addToWatch[lang]}
          allLabel={T.wlFilterAll[lang]}
          onSave={onSave}
          onSelect={onSelectFilm}
        />
      </section>

      <style>{styles}</style>
    </div>
  );
}

function SettingsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="m19.4 15-.4-1c.3-.5.5-1.1.6-1.7l1.3-.5a8.8 8.8 0 0 0 0-3.6l-1.3-.5a6.1 6.1 0 0 0-.6-1.7l.4-1-2.6-2.6-1 .4a6.1 6.1 0 0 0-1.7-.6l-.5-1.3a8.8 8.8 0 0 0-3.6 0l-.5 1.3c-.6.1-1.2.3-1.7.6l-1-.4-2.6 2.6.4 1c-.3.5-.5 1.1-.6 1.7l-1.3.5a8.8 8.8 0 0 0 0 3.6l1.3.5c.1.6.3 1.2.6 1.7l-.4 1 2.6 2.6 1-.4c.5.3 1.1.5 1.7.6l.5 1.3a8.8 8.8 0 0 0 3.6 0l.5-1.3c.6-.1 1.2-.3 1.7-.6l1 .4 2.6-2.6Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export { SAMPLE_RECS };

const styles = `
.we-hero {
  max-width: 390px;
  margin: 24px auto 0;
  padding: 18px 18px 20px;
  background: var(--color-wine);
  border: 1px solid var(--wine-light-border);
  border-radius: 22px;
  margin-left: 20px;
  margin-right: 20px;
}
@media (min-width: 411px) {
  .we-hero { margin-left: auto; margin-right: auto; width: calc(100% - 40px); max-width: 350px; }
}
.we-hero__title {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 16px;
  color: var(--color-cream);
  margin-bottom: 6px;
}
.we-hero__sub {
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 18px;
  color: var(--cream-70);
}
.we-hero__books {
  margin-top: 14px;
  height: 36px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid var(--gold-border);
  background: var(--gold-tint-strong);
  color: var(--color-cream);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}
.we-hero__books:hover { background: var(--gold-tint-medium); }

.we-recs {
  max-width: 390px;
  margin: 32px auto 0;
  padding: 0 20px 40px;
}
.we-recs__eyebrow {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 2.4px;
  text-transform: uppercase;
  color: var(--color-gold);
  margin-bottom: 6px;
}
.we-recs__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 20px;
  letter-spacing: -0.3px;
  color: var(--color-cream);
  margin-bottom: 18px;
}
`;
