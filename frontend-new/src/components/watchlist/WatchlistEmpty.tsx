import { useState } from 'react';
import { useSettings } from '../../settings';
import { T } from '../../i18n';
import type { RecFilm } from './WatchlistMain';
import { SAMPLE_RECS, LangToggle, SearchIcon, AccountButton } from './WatchlistMain';
import { CuratedGrid } from './CuratedGrid';
import { BookSearchSheet } from '../BookSearchSheet';

interface Props {
  userName: string;
  curated: RecFilm[];
  bookCount: number;
  onOpenAuth: () => void;
  onOpenSearch: () => void;
  onOpenBooks: () => void;
  onSave: (film: RecFilm) => void;
  onSelectFilm: (film: RecFilm) => void;
}

type Tab = 'movies' | 'books';

export function WatchlistEmpty({
  userName, curated, bookCount, onOpenAuth, onOpenSearch, onOpenBooks, onSave, onSelectFilm,
}: Props) {
  const { lang, setLang } = useSettings();
  const [tab, setTab] = useState<Tab>('movies');
  const [searchOpen, setSearchOpen] = useState(false);

  // Inline book search reuses the standalone sheet (guest-safe via useBooks).
  // The tab state above persists because this component never unmounts.
  if (searchOpen) {
    return <BookSearchSheet onClose={() => setSearchOpen(false)} />;
  }

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
      </section>

      <div className="we-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          className={`we-tab${tab === 'movies' ? ' is-active' : ''}`}
          aria-selected={tab === 'movies'}
          onClick={() => setTab('movies')}
        >
          🎬 {T.wlFilterMovies[lang]}
        </button>
        <button
          type="button"
          role="tab"
          className={`we-tab${tab === 'books' ? ' is-active' : ''}`}
          aria-selected={tab === 'books'}
          onClick={() => setTab('books')}
        >
          📚 {T.wlFilterBooks[lang]}
        </button>
      </div>

      {tab === 'movies' ? (
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
      ) : (
        <section className="we-books">
          <div className="we-recs__eyebrow">{T.wlBooksEyebrow[lang]}</div>
          <div className="we-recs__title">{T.wlBooksTitle[lang]}</div>
          <div className="we-books__sub">{T.booksEmptySub[lang]}</div>
          <button type="button" className="we-books__cta" onClick={() => setSearchOpen(true)}>
            📚 {T.booksFindCta[lang]} →
          </button>
          {bookCount > 0 && (
            <button type="button" className="we-books__link" onClick={onOpenBooks}>
              {T.wlBooksOpenList[lang]}
            </button>
          )}
        </section>
      )}

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

.we-tabs {
  display: flex;
  gap: 6px;
  max-width: 390px;
  margin: 28px auto 0;
  padding: 4px;
  background: var(--color-wine);
  border: 1px solid var(--wine-light-border);
  border-radius: 14px;
  width: calc(100% - 40px);
}
.we-tab {
  flex: 1;
  height: 38px;
  border-radius: 10px;
  border: 0;
  background: transparent;
  color: var(--cream-70);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.we-tab:hover { color: var(--color-cream); }
.we-tab.is-active {
  background: var(--gold-tint-strong);
  color: var(--color-cream);
}

.we-recs {
  max-width: 390px;
  margin: 20px auto 0;
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

.we-books {
  max-width: 390px;
  margin: 20px auto 0;
  padding: 0 20px 40px;
}
.we-books__sub {
  font-family: var(--font-body);
  font-size: 14px;
  line-height: 20px;
  color: var(--cream-70);
  margin-bottom: 18px;
}
.we-books__cta {
  height: 44px;
  padding: 0 20px;
  border-radius: 12px;
  border: 1px solid var(--gold-border);
  background: var(--gold-tint-strong);
  color: var(--color-cream);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
}
.we-books__cta:hover { background: var(--gold-tint-medium); }
.we-books__link {
  display: block;
  margin-top: 16px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-gold);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
}
.we-books__link:hover { text-decoration: underline; }
`;
