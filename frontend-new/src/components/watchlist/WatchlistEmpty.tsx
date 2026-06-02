import { useSettings } from '../../settings';
import { T } from '../../i18n';
import type { RecFilm } from './WatchlistMain';
import { SAMPLE_RECS, LangToggle, SearchIcon, AccountButton } from './WatchlistMain';
import { CuratedGrid } from './CuratedGrid';

interface Props {
  userName: string;
  curated: RecFilm[];
  onOpenAuth: () => void;
  onOpenSearch: () => void;
  onOpenBooks: () => void;
  onSave: (film: RecFilm) => void;
  onSelectFilm: (film: RecFilm) => void;
}

export function WatchlistEmpty({
  userName, curated, onOpenAuth, onOpenSearch, onOpenBooks, onSave, onSelectFilm,
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
          <AccountButton onSignIn={onOpenAuth} />
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
