import { useState } from 'react';

interface Film {
  id: string;
  title: string;
  /** Russian accusative form ("Запустить Анору"). Falls back to `title` if absent. */
  titleAccusative?: string;
  award?: string;
  year: number;
  genre: string;
  runtime: string;
  rating: number;
  rationale: string;
  source: string;
  streaming?: string;
  /** CSS background string for the stylized poster (gradient + decoration). */
  poster: {
    background: string;
    /** Title shown vertically inside the poster. */
    overlay: string;
    overlayColor?: string;
  };
}

interface Props {
  open: boolean;
  mood: string;
  duration?: string | null;
  films: Film[];
  loading?: boolean;
  onClose: () => void;
  onRefine: () => void;
  onLaunch: (film: Film) => void;
}

export function TonightResults({
  open, mood, duration, films, loading = false, onClose, onRefine, onLaunch,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(films[0]?.id ?? null);

  if (!open) return null;

  const selected = films.find((f) => f.id === selectedId) ?? films[0];
  const breadcrumb = duration ? `${mood} · ${duration}` : mood;

  return (
    <div className="lt-screen" role="dialog" aria-modal="true" aria-label="Подобрала на вечер">
      <StarFieldResults />

      <button className="ltr-back" onClick={onClose} aria-label="Назад">
        <BackIcon />
      </button>

      <div className="ltr-inner">
        <div className="ltr-breadcrumb">{breadcrumb}</div>
        <h1 className="ltr-title">Подобрала<br />на вечер</h1>
        <div className="ltr-subtitle">Из твоего списка · {films.length} фильма</div>

        <div className="ltr-cards">
          {films.map((film) => (
            <FilmResultCard
              key={film.id}
              film={film}
              selected={film.id === selectedId}
              onSelect={() => setSelectedId(film.id)}
            />
          ))}
        </div>

      </div>

      <div className="ltr-cta-dock">
        <button
          type="button"
          className="ltr-refine"
          onClick={onRefine}
        >
          Не подошли — <span className="ltr-refine__accent">подобрать ещё</span>
        </button>
        <button
          type="button"
          className="ltr-cta"
          onClick={() => selected && onLaunch(selected)}
          disabled={loading || !selected}
        >
          {selected ? `Запустить ${selected.titleAccusative ?? selected.title}` : 'Запустить'}
        </button>
      </div>

      <style>{styles}</style>
    </div>
  );
}

function FilmResultCard({
  film, selected, onSelect,
}: {
  film: Film;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={`ltr-card${selected ? ' is-selected' : ''}`}
      onClick={onSelect}
      aria-pressed={selected}
    >
      <div
        className="ltr-card__poster"
        style={{ background: film.poster.background }}
      >
        <div
          className="ltr-card__poster-overlay"
          style={{ color: film.poster.overlayColor ?? 'rgba(255,255,255,0.95)' }}
        >
          {film.poster.overlay}
        </div>
      </div>

      <div className="ltr-card__body">
        {film.award && <div className="ltr-card__eyebrow">{film.award}</div>}
        <div className="ltr-card__title">{film.title}</div>
        <div className="ltr-card__meta">
          {film.year} · {film.genre} · {film.runtime} · ★ {film.rating.toFixed(1)}
        </div>
        <div className="ltr-card__rationale">«{film.rationale}»</div>
        <div className="ltr-card__bottom-row">
          <span className="ltr-card__source">{film.source}</span>
          {film.streaming && (
            <span className="ltr-card__streaming">{film.streaming}</span>
          )}
        </div>
      </div>
    </button>
  );
}

function BackIcon() {
  return (
    <svg width="11" height="18" viewBox="0 0 11 18" fill="none" aria-hidden>
      <path d="M9 1L2 9L9 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StarFieldResults() {
  const stars = [
    { x: '64%', y: '4%', r: 1.2, o: 0.50 },
    { x: '82%', y: '8%', r: 1.0, o: 0.35 },
    { x: '40%', y: '12%', r: 0.8, o: 0.30 },
  ];
  return (
    <div className="ltr-stars" aria-hidden>
      {stars.map((s, i) => (
        <span
          key={i}
          style={{
            left: s.x,
            top: s.y,
            width: s.r * 2,
            height: s.r * 2,
            opacity: s.o,
          }}
        />
      ))}
    </div>
  );
}

/** Sample data for the standalone preview route. */
export const SAMPLE_FILMS: Film[] = [
  {
    id: 'anora',
    title: 'Анора',
    titleAccusative: 'Анору',
    award: "PALME D'OR",
    year: 2024,
    genre: 'драма',
    runtime: '2 ч 19 мин',
    rating: 7.6,
    rationale: 'Тяжёлая в эмоциях, но точная — под уют.',
    source: '📷 из Instagram',
    streaming: 'Кинопоиск',
    poster: {
      background: 'linear-gradient(160deg, #E91E63 0%, #B12055 45%, #5E0823 100%)',
      overlay: 'ANORA',
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
    rationale: 'Без слов, только движение и тишина — медитативно.',
    source: '📢 из Кинопремия',
    streaming: 'Apple TV+',
    poster: {
      background: 'linear-gradient(155deg, #2C7E7A 0%, #1A4F4D 55%, #0B2A28 100%)',
      overlay: 'ПОТОК',
    },
  },
  {
    id: 'poor-things',
    title: 'Бедные несчастные',
    titleAccusative: 'Бедных несчастных',
    award: 'GOLDEN LION',
    year: 2023,
    genre: 'драма',
    runtime: '2 ч 21 мин',
    rating: 8.0,
    rationale: 'Странное и красивое — если хочется особенного.',
    source: '📷 из @kinokanal',
    poster: {
      background: 'linear-gradient(150deg, #E8C76A 0%, #BF8E2A 50%, #6B4814 100%)',
      overlay: 'БЕДНЫЕ\nНЕСЧАСТНЫЕ',
      overlayColor: 'rgba(60, 28, 8, 0.85)',
    },
  },
];

const styles = `
.ltr-stars {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  max-width: 390px;
  left: 50%;
  transform: translateX(-50%);
  height: 200px;
}
.ltr-stars > span {
  position: absolute;
  border-radius: 50%;
  background: var(--color-cream);
  display: block;
}

.ltr-back {
  position: absolute;
  top: 56px;
  left: 50%;
  transform: translateX(-175px);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--wine-light-border);
  background: var(--color-wine);
  color: var(--color-cream);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  z-index: 2;
  transition: background 0.15s ease;
}
.ltr-back:hover { background: var(--color-wine-light); }
.ltr-back:focus-visible {
  outline: 2px solid var(--gold-border-strong);
  outline-offset: 2px;
}

.ltr-inner {
  max-width: 390px;
  margin: 0 auto;
  padding: 96px 20px 160px;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

.ltr-breadcrumb {
  align-self: flex-start;
  margin-left: 48px; /* clear of back button */
  height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border-radius: 14px;
  background: var(--gold-tint-light);
  border: 1px solid rgba(228, 177, 92, 0.35);
  color: var(--color-gold);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 13px;
  margin-top: -36px; /* sit beside the back button */
  margin-bottom: 28px;
}

.ltr-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 40px;
  line-height: 46px;
  letter-spacing: -1.5px;
  color: var(--color-cream);
  margin: 0 0 16px;
}

.ltr-subtitle {
  font-family: var(--font-body);
  font-size: 14px;
  color: rgba(233, 217, 167, 0.6);
  margin-bottom: 18px;
}

.ltr-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ltr-card {
  display: flex;
  gap: 12px;
  width: 100%;
  min-height: 156px;
  padding: 12px;
  border-radius: 20px;
  border: 1px solid var(--wine-light-border);
  background: var(--color-wine);
  color: var(--color-cream);
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.ltr-card:hover { border-color: rgba(90, 55, 96, 0.7); }
.ltr-card:focus-visible {
  outline: 2px solid var(--gold-border-strong);
  outline-offset: 2px;
}
.ltr-card.is-selected {
  background: linear-gradient(0deg, var(--gold-tint-subtle), var(--gold-tint-subtle)), var(--color-wine);
  border-color: var(--gold-border-strong);
}

.ltr-card__poster {
  flex: 0 0 auto;
  width: 92px;
  height: 132px;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  padding: 10px;
}
.ltr-card__poster-overlay {
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 1.5px;
  line-height: 14px;
  white-space: pre-line;
  text-transform: uppercase;
}

.ltr-card__body {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.ltr-card__eyebrow {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 10px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: var(--color-gold);
  margin-bottom: 6px;
}

.ltr-card__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 20px;
  line-height: 24px;
  letter-spacing: -0.3px;
  color: var(--color-cream);
  margin-bottom: 6px;
}

.ltr-card__meta {
  font-family: var(--font-body);
  font-weight: 400;
  font-size: 12px;
  color: rgba(233, 217, 167, 0.6);
  margin-bottom: 8px;
}

.ltr-card__rationale {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 400;
  font-size: 13px;
  line-height: 18px;
  color: rgba(233, 217, 167, 0.92);
  margin-bottom: auto;
}

.ltr-card__bottom-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  gap: 8px;
}
.ltr-card__source {
  font-family: var(--font-body);
  font-size: 11px;
  color: rgba(233, 217, 167, 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ltr-card__streaming {
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

.ltr-refine {
  border: 0;
  background: transparent;
  font-family: var(--font-body);
  font-size: 13px;
  color: rgba(233, 217, 167, 0.6);
  cursor: pointer;
  padding: 6px 4px 10px;
}
.ltr-refine__accent {
  color: var(--color-gold);
  font-weight: 600;
}

.ltr-cta-dock {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 20px 24px;
  background: linear-gradient(to top, var(--color-wine-deep) 65%, rgba(42, 24, 48, 0));
  z-index: 3;
  pointer-events: none;
}
.ltr-cta-dock > * { pointer-events: auto; }
.ltr-cta {
  width: 100%;
  max-width: 350px;
  height: 56px;
  border-radius: var(--radius-pill);
  border: 0;
  background: var(--color-gold);
  color: var(--color-wine-deep);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.ltr-cta:hover { background: var(--color-gold-dark); }
.ltr-cta:disabled { cursor: wait; opacity: 0.7; }
.ltr-cta:focus-visible {
  outline: 2px solid var(--color-cream);
  outline-offset: 3px;
}

@media (max-width: 420px) {
  .ltr-back { transform: none; left: 16px; }
}
`;
