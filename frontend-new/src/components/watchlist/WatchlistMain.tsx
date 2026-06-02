import { useState } from 'react';
import { useSettings } from '../../settings';
import { T, type Lang } from '../../i18n';

export interface SavedFilm {
  id: string;
  title: string;
  award?: string;
  year: number;
  genre: string;
  runtime: string;
  rating: number;
  /** Italic 'why-saved' phrase that preserves the original recommendation's emotional energy. */
  italic: string;
  source: string;
  streaming?: string;
  poster: {
    background: string;
    overlay: string;
    overlayColor?: string;
  };
}

export interface RecFilm {
  id: string;
  title: string;
  director: string;
  year: number;
  award?: string;
  poster: {
    background: string;
    /** Single styling-config object so cards can render their per-film art. */
    overlay: string;
    overlayColor?: string;
    overlayFont?: 'display-italic' | 'display-bold' | 'body-caps';
    overlayDecoration?: 'vertical-lines' | 'horizontal-line' | 'radial-glow';
  };
}

interface Props {
  userName: string;
  films: SavedFilm[];
  recommendations: RecFilm[];
  bookCount?: number;
  onOpenTonight: () => void;
  onOpenSettings: () => void;
  onOpenSearch: () => void;
  onOpenBooks: () => void;
  onSelectFilm: (film: SavedFilm) => void;
  onSelectRec: (film: RecFilm) => void;
  onSeeAllAwards: () => void;
}

type Filter = 'all' | 'movies' | 'series';

export function WatchlistMain({
  userName, films, recommendations, bookCount = 0,
  onOpenTonight, onOpenSettings, onOpenSearch, onOpenBooks,
  onSelectFilm, onSelectRec, onSeeAllAwards,
}: Props) {
  const { lang, setLang } = useSettings();
  const [filter, setFilter] = useState<Filter>('all');

  const counts = {
    all: films.length,
    movies: films.length, // no series flag in the data yet — placeholder
    series: 0,
    books: bookCount,
  };

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

      <section className="wl-tonight-cta">
        <button className="wl-tonight-cta__btn" onClick={onOpenTonight}>
          <span className="wl-tonight-cta__emoji" aria-hidden>🌙</span>
          <span className="wl-tonight-cta__text">
            <span className="wl-tonight-cta__eyebrow">{T.tonightEyebrow[lang]}</span>
            <span className="wl-tonight-cta__title">{T.tonightTitle[lang]}</span>
            <span className="wl-tonight-cta__subtitle">{T.tonightSubtitle[lang]}</span>
          </span>
          <span className="wl-tonight-cta__arrow" aria-hidden>→</span>
        </button>
      </section>

      <section className="wl-filters">
        <FilterChip
          label={T.wlFilterAll[lang]}
          count={counts.all}
          active={filter === 'all'}
          onClick={() => setFilter('all')}
        />
        <FilterChip
          label={T.wlFilterMovies[lang]}
          count={counts.movies}
          active={filter === 'movies'}
          onClick={() => setFilter('movies')}
        />
        <FilterChip
          label={T.wlFilterSeries[lang]}
          count={counts.series}
          active={filter === 'series'}
          onClick={() => setFilter('series')}
        />
        <FilterChip label={T.wlFilterBooks[lang]} count={counts.books} onClick={onOpenBooks} />
      </section>

      <section className="wl-saved">
        <div className="wl-section-header">
          <div className="wl-section-title">{T.wlRecent[lang]}</div>
          <button className="wl-sort" type="button">{T.wlSortByDate[lang]}</button>
        </div>
        <div className="wl-saved-list">
          {films.map((film) => (
            <SavedFilmCard key={film.id} film={film} onClick={() => onSelectFilm(film)} />
          ))}
        </div>
      </section>

      <section className="wl-recs">
        <div className="wl-recs__head">
          <div>
            <div className="wl-recs__eyebrow">{T.wlRecsEyebrow[lang]}</div>
            <div className="wl-recs__title">{T.wlRecsTitle[lang]}</div>
          </div>
          <button className="wl-recs__see-all" onClick={onSeeAllAwards}>{T.wlSeeAll[lang]}</button>
        </div>
        <div className="wl-recs__row">
          {recommendations.map((rec) => (
            <RecCard key={rec.id} rec={rec} onClick={() => onSelectRec(rec)} />
          ))}
        </div>
      </section>

      <style>{styles}</style>
    </div>
  );
}

function FilterChip({
  label, count, active = false, disabled = false, onClick,
}: {
  label: string;
  count: number;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className={`wl-chip${active ? ' is-active' : ''}${disabled ? ' is-disabled' : ''}`}
      onClick={onClick}
      disabled={disabled}
    >
      <span className="wl-chip__label">{label}</span>
      <span className="wl-chip__count">{count}</span>
    </button>
  );
}

function SavedFilmCard({ film, onClick }: { film: SavedFilm; onClick: () => void }) {
  return (
    <button type="button" className="wl-card" onClick={onClick}>
      <div
        className="wl-card__poster"
        style={{ background: film.poster.background }}
      >
        <div
          className="wl-card__poster-overlay"
          style={{ color: film.poster.overlayColor ?? 'rgba(255,255,255,0.95)' }}
        >
          {film.poster.overlay}
        </div>
      </div>
      <div className="wl-card__body">
        {film.award && <div className="wl-card__eyebrow">{film.award}</div>}
        <div className="wl-card__title">{film.title}</div>
        <div className="wl-card__meta">
          {film.year} · {film.genre} · {film.runtime} · ★ {film.rating.toFixed(1)}
        </div>
        <div className="wl-card__italic">«{film.italic}»</div>
        <div className="wl-card__bottom">
          <span className="wl-card__source">{film.source}</span>
          {film.streaming && (
            <span
              className={`wl-card__streaming${film.streaming === 'Кинопоиск' ? '' : ' is-neutral'}`}
            >
              {film.streaming}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

function RecCard({ rec, onClick }: { rec: RecFilm; onClick: () => void }) {
  return (
    <button type="button" className="wl-rec" onClick={onClick}>
      <div
        className="wl-rec__poster"
        style={{ background: rec.poster.background }}
      >
        {rec.award && <span className="wl-rec__badge">{rec.award}</span>}
        <div
          className={`wl-rec__overlay wl-rec__overlay--${rec.poster.overlayFont ?? 'display-italic'}`}
          style={{ color: rec.poster.overlayColor ?? 'rgba(255,255,255,0.95)' }}
        >
          {rec.poster.overlay}
        </div>
        {rec.poster.overlayDecoration === 'vertical-lines' && <DecorVerticalLines />}
        {rec.poster.overlayDecoration === 'horizontal-line' && <DecorHorizontalLine />}
      </div>
      <div className="wl-rec__title">{rec.title}</div>
      <div className="wl-rec__meta">{rec.director} · {rec.year}</div>
    </button>
  );
}

/** Always-visible RU/EN switch in the header so a non-Russian visitor can
 *  immediately flip the language without digging into settings. */
export function LangToggle({ lang, setLang }: { lang: Lang; setLang: (l: Lang) => void }) {
  return (
    <div className="wl-lang" role="group" aria-label="Language">
      {(['ru', 'en'] as Lang[]).map((l) => (
        <button
          key={l}
          type="button"
          className={`wl-lang__btn${lang === l ? ' is-active' : ''}`}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

export function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.6" />
      <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path
        d="m19.4 15-.4-1c.3-.5.5-1.1.6-1.7l1.3-.5a8.8 8.8 0 0 0 0-3.6l-1.3-.5a6.1 6.1 0 0 0-.6-1.7l.4-1-2.6-2.6-1 .4a6.1 6.1 0 0 0-1.7-.6l-.5-1.3a8.8 8.8 0 0 0-3.6 0l-.5 1.3c-.6.1-1.2.3-1.7.6l-1-.4-2.6 2.6.4 1c-.3.5-.5 1.1-.6 1.7l-1.3.5a8.8 8.8 0 0 0 0 3.6l1.3.5c.1.6.3 1.2.6 1.7l-.4 1 2.6 2.6 1-.4c.5.3 1.1.5 1.7.6l.5 1.3a8.8 8.8 0 0 0 3.6 0l.5-1.3c.6-.1 1.2-.3 1.7-.6l1 .4 2.6-2.6Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DecorVerticalLines() {
  return (
    <svg className="wl-rec__decor" viewBox="0 0 130 170" fill="none" preserveAspectRatio="none" aria-hidden>
      <line x1="40" y1="20" x2="40" y2="150" stroke="rgba(255,255,255,0.25)" strokeWidth="1.2" />
      <line x1="65" y1="20" x2="65" y2="150" stroke="rgba(255,255,255,0.25)" strokeWidth="1.2" />
      <line x1="90" y1="20" x2="90" y2="150" stroke="rgba(255,255,255,0.25)" strokeWidth="1.2" />
    </svg>
  );
}

function DecorHorizontalLine() {
  return (
    <svg className="wl-rec__decor" viewBox="0 0 130 170" fill="none" preserveAspectRatio="none" aria-hidden>
      <line x1="0" y1="102" x2="130" y2="102" stroke="rgba(255,255,255,0.35)" strokeWidth="1.2" />
    </svg>
  );
}

/** Sample data for standalone preview. */
export const SAMPLE_SAVED: SavedFilm[] = [
  {
    id: 'anora',
    title: 'Анора',
    award: "PALME D'OR",
    year: 2024,
    genre: 'драма',
    runtime: '2 ч 19 мин',
    rating: 7.6,
    italic: 'Просто шок — пост в Instagram',
    source: '📷 из Instagram',
    streaming: 'Кинопоиск',
    poster: {
      background: 'linear-gradient(160deg, #E91E63 0%, #B12055 45%, #5E0823 100%)',
      overlay: 'ANORA',
    },
  },
  {
    id: 'dune-2',
    title: 'Дюна: Часть 2',
    year: 2024,
    genre: 'фантастика',
    runtime: '2 ч 46 мин',
    rating: 8.5,
    italic: 'Эпично, must watch — от Маши',
    source: '💬 от Маши',
    streaming: 'Кинопоиск',
    poster: {
      background: 'linear-gradient(155deg, #D88B3C 0%, #A95B1F 50%, #3F1F0E 100%)',
      overlay: 'ДЮНА',
    },
  },
  {
    id: 'flow',
    title: 'Поток',
    award: 'OSCAR',
    year: 2024,
    genre: 'анимация',
    runtime: '1 ч 24 мин',
    rating: 8.2,
    italic: 'Без слов, только движение — канал',
    source: '📢 @kinotok',
    streaming: 'Apple TV+',
    poster: {
      background: 'linear-gradient(155deg, #2C7E7A 0%, #1A4F4D 55%, #0B2A28 100%)',
      overlay: 'ПОТОК',
    },
  },
  {
    id: 'poor-things',
    title: 'Бедные несчастные',
    award: 'GOLDEN LION',
    year: 2023,
    genre: 'драма',
    runtime: '2 ч 21 мин',
    rating: 8.0,
    italic: 'Странное и красивое — пост',
    source: '📷 @kinokanal',
    streaming: 'Кинопоиск',
    poster: {
      background: 'linear-gradient(150deg, #E8C76A 0%, #BF8E2A 50%, #6B4814 100%)',
      overlay: 'БЕДНЫЕ\nНЕСЧАСТНЫЕ',
      overlayColor: 'rgba(60, 28, 8, 0.85)',
    },
  },
];

export const SAMPLE_RECS: RecFilm[] = [
  {
    id: 'anora',
    title: 'Anora',
    director: 'Sean Baker',
    year: 2024,
    award: "PALME D'OR",
    poster: {
      background: 'linear-gradient(160deg, #E91E63 0%, #5E0823 100%)',
      overlay: 'Anora',
      overlayFont: 'display-italic',
    },
  },
  {
    id: 'brutalist',
    title: 'The Brutalist',
    director: 'Brady Corbet',
    year: 2024,
    award: 'GOLDEN GLOBE',
    poster: {
      background: 'linear-gradient(170deg, #7D7568 0%, #4A4234 50%, #2A1F12 100%)',
      overlay: 'THE\nBRUTALIST',
      overlayFont: 'body-caps',
      overlayDecoration: 'vertical-lines',
    },
  },
  {
    id: 'anatomy',
    title: 'Anatomy of a Fall',
    director: 'Justine Triet',
    year: 2023,
    award: "PALME D'OR",
    poster: {
      background: 'linear-gradient(170deg, #3D5E7A 0%, #1F3548 50%, #0E1A2A 100%)',
      overlay: 'ANATOMY\nOF A FALL',
      overlayFont: 'body-caps',
      overlayDecoration: 'horizontal-line',
    },
  },
  {
    id: 'oppenheimer',
    title: 'Oppenheimer',
    director: 'Christopher Nolan',
    year: 2023,
    award: 'OSCAR',
    poster: {
      background: 'radial-gradient(circle at 50% 40%, #E89A3F 0%, #C44A1A 40%, #5E1707 75%, #2A0A05 100%)',
      overlay: 'OPPEN-\nHEIMER',
      overlayFont: 'display-bold',
    },
  },
  {
    id: 'substance',
    title: 'The Substance',
    director: 'Coralie Fargeat',
    year: 2024,
    poster: {
      background: 'linear-gradient(165deg, #E8E0CC 0%, #C5B8A0 50%, #6B5C44 100%)',
      overlay: 'THE\nSUBSTANCE',
      overlayFont: 'body-caps',
      overlayColor: 'rgba(40, 20, 10, 0.85)',
    },
  },
  {
    id: 'parasite',
    title: 'Parasite',
    director: 'Bong Joon-ho',
    year: 2019,
    award: 'OSCAR',
    poster: {
      background: 'linear-gradient(160deg, #5C3B2A 0%, #2F1E14 50%, #100806 100%)',
      overlay: 'PARASITE',
      overlayFont: 'body-caps',
    },
  },
];

const styles = `
.wl-tonight-cta {
  max-width: 390px;
  margin: 24px auto 0;
  padding: 0 20px;
}
.wl-tonight-cta__btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  height: 96px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(228, 177, 92, 0.22) 0%, rgba(228, 177, 92, 0.05) 100%);
  border: 1px solid rgba(228, 177, 92, 0.40);
  color: var(--color-cream);
  font-family: inherit;
  cursor: pointer;
  text-align: left;
  transition: filter 0.15s ease;
}
.wl-tonight-cta__btn:hover { filter: brightness(1.1); }
.wl-tonight-cta__emoji {
  font-size: 30px;
  line-height: 1;
  flex: 0 0 auto;
}
.wl-tonight-cta__text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.wl-tonight-cta__eyebrow {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--color-gold);
}
.wl-tonight-cta__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 19px;
  letter-spacing: -0.3px;
  color: var(--color-cream);
}
.wl-tonight-cta__subtitle {
  font-family: var(--font-body);
  font-size: 12px;
  color: rgba(233, 217, 167, 0.7);
}
.wl-tonight-cta__arrow {
  font-size: 22px;
  color: var(--color-gold);
  flex: 0 0 auto;
}

.wl-filters {
  max-width: 390px;
  margin: 32px auto 0;
  padding: 0 20px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.wl-chip {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border-radius: 16px;
  border: 1px solid var(--wine-light-border);
  background: var(--color-wine);
  color: rgba(233, 217, 167, 0.85);
  font-family: var(--font-body);
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.wl-chip:hover:not(.is-disabled) { border-color: rgba(90, 55, 96, 0.7); }
.wl-chip__label {
  font-size: 14px;
  font-weight: 400;
}
.wl-chip__count {
  font-size: 12px;
  color: rgba(233, 217, 167, 0.5);
}
.wl-chip.is-active {
  background: var(--gold-tint-strong);
  border-color: var(--gold-border);
  color: var(--color-cream);
}
.wl-chip.is-active .wl-chip__label { font-weight: 600; }
.wl-chip.is-active .wl-chip__count { color: var(--color-gold); }
.wl-chip.is-disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.wl-saved {
  max-width: 390px;
  margin: 28px auto 0;
  padding: 0 20px;
}

.wl-section-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
}
.wl-section-title {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 16px;
  color: var(--color-cream);
}
.wl-sort {
  border: 0;
  background: transparent;
  font-family: var(--font-body);
  font-size: 13px;
  color: rgba(233, 217, 167, 0.6);
  cursor: pointer;
  padding: 4px 0;
}

.wl-saved-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wl-card {
  display: flex;
  gap: 12px;
  width: 100%;
  min-height: 168px;
  padding: 10px;
  border-radius: 20px;
  border: 1px solid var(--wine-light-border);
  background: var(--color-wine);
  color: var(--color-cream);
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.wl-card:hover { border-color: rgba(90, 55, 96, 0.7); }

.wl-card__poster {
  flex: 0 0 auto;
  width: 100px;
  height: 140px;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  padding: 10px;
}
.wl-card__poster-overlay {
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 1.5px;
  line-height: 14px;
  white-space: pre-line;
  text-transform: uppercase;
}

.wl-card__body {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.wl-card__eyebrow {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 10px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: var(--color-gold);
  margin-bottom: 6px;
}

.wl-card__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 20px;
  line-height: 24px;
  letter-spacing: -0.3px;
  color: var(--color-cream);
  margin-bottom: 6px;
}

.wl-card__meta {
  font-family: var(--font-body);
  font-weight: 400;
  font-size: 12px;
  color: rgba(233, 217, 167, 0.6);
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wl-card__italic {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 400;
  font-size: 13px;
  line-height: 18px;
  color: rgba(233, 217, 167, 0.92);
  margin-bottom: auto;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.wl-card__bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.wl-card__source {
  font-family: var(--font-body);
  font-size: 11px;
  color: rgba(233, 217, 167, 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wl-card__streaming {
  flex: 0 0 auto;
  height: 20px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  border-radius: 4px;
  background: rgba(228, 177, 92, 0.15);
  color: var(--color-gold);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 10px;
}
.wl-card__streaming.is-neutral {
  background: rgba(160, 175, 200, 0.12);
  color: rgba(213, 224, 240, 0.85);
}

.wl-recs {
  max-width: 390px;
  margin: 40px auto 0;
  padding-bottom: 56px;
}

.wl-recs__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 0 20px;
  margin-bottom: 14px;
}
.wl-recs__eyebrow {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 2.4px;
  text-transform: uppercase;
  color: var(--color-gold);
  margin-bottom: 6px;
}
.wl-recs__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 20px;
  letter-spacing: -0.3px;
  color: var(--color-cream);
}
.wl-recs__see-all {
  border: 0;
  background: transparent;
  color: var(--color-gold);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  padding: 4px 0;
}

.wl-recs__row {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  overflow-y: visible;
  padding: 0 20px 8px;
  scroll-snap-type: x proximity;
  scrollbar-width: none;
}
.wl-recs__row::-webkit-scrollbar { display: none; }

.wl-rec {
  flex: 0 0 auto;
  width: 130px;
  display: flex;
  flex-direction: column;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
  text-align: left;
  scroll-snap-align: start;
}

.wl-rec__poster {
  width: 130px;
  height: 170px;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  margin-bottom: 8px;
}

.wl-rec__badge {
  position: absolute;
  top: 8px;
  left: 8px;
  height: 18px;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
  background: rgba(228, 177, 92, 0.85);
  color: var(--color-wine-deep);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 8.5px;
  letter-spacing: 1px;
  border-radius: 3px;
  z-index: 1;
}

.wl-rec__overlay {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  white-space: pre-line;
  z-index: 1;
}
.wl-rec__overlay--display-italic {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 400;
  font-size: 26px;
  line-height: 28px;
  letter-spacing: -0.5px;
}
.wl-rec__overlay--display-bold {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 16px;
  line-height: 18px;
  letter-spacing: 0.5px;
}
.wl-rec__overlay--body-caps {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 14px;
  line-height: 16px;
  letter-spacing: 1.5px;
}

.wl-rec__decor {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.wl-rec__title {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12px;
  color: var(--color-cream);
  margin-bottom: 3px;
}

.wl-rec__meta {
  font-family: var(--font-body);
  font-size: 10px;
  color: rgba(233, 217, 167, 0.6);
}
`;
