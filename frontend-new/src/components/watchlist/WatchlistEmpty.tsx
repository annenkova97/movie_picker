import { useState } from 'react';
import type { RecFilm } from './WatchlistMain';
import { SAMPLE_RECS } from './WatchlistMain';

type AwardFilter = 'all' | 'oscar' | 'palme' | 'golden-globe';

interface Props {
  userName: string;
  curated: RecFilm[];
  onOpenSettings: () => void;
  onSave: (film: RecFilm) => void;
  onSelectFilm: (film: RecFilm) => void;
}

const FILTER_LABELS: { key: AwardFilter; label: string }[] = [
  { key: 'all', label: 'Все' },
  { key: 'oscar', label: 'Oscar' },
  { key: 'palme', label: "Palme d'Or" },
  { key: 'golden-globe', label: 'Golden Globe' },
];

const AWARD_KEYS: Record<AwardFilter, (award?: string) => boolean> = {
  all: () => true,
  oscar: (a) => a === 'OSCAR',
  palme: (a) => a === "PALME D'OR",
  'golden-globe': (a) => a === 'GOLDEN GLOBE',
};

export function WatchlistEmpty({
  userName, curated, onOpenSettings, onSave, onSelectFilm,
}: Props) {
  const [filter, setFilter] = useState<AwardFilter>('all');
  const films = curated.filter((f) => AWARD_KEYS[filter](f.award));

  return (
    <div className="lt-screen wl-screen">
      <header className="wl-header">
        <div>
          <div className="wl-greeting">Привет, {userName} <span aria-hidden>🎬</span></div>
          <h1 className="wl-title">Хочу посмотреть</h1>
        </div>
        <button className="wl-settings" onClick={onOpenSettings} aria-label="Настройки">
          <SettingsIcon />
        </button>
      </header>

      <section className="we-hero">
        <div className="we-hero__title">Здесь пока пусто <span aria-hidden>🎬</span></div>
        <div className="we-hero__sub">
          Сохраняй фильмы из соцсетей, от друзей — или начни с лучшего ниже ↓
        </div>
      </section>

      <section className="we-recs">
        <div className="we-recs__eyebrow">Стоит посмотреть</div>
        <div className="we-recs__title">Фильмы с номинацией</div>

        <div className="we-filters">
          {FILTER_LABELS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              className={`we-filter${filter === key ? ' is-active' : ''}`}
              onClick={() => setFilter(key)}
              aria-pressed={filter === key}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="we-grid">
          {films.map((film) => (
            <CuratedCard
              key={film.id}
              film={film}
              onSave={() => onSave(film)}
              onClick={() => onSelectFilm(film)}
            />
          ))}
        </div>
      </section>

      <style>{styles}</style>
    </div>
  );
}

function CuratedCard({
  film, onSave, onClick,
}: {
  film: RecFilm;
  onSave: () => void;
  onClick: () => void;
}) {
  return (
    <div className="we-card">
      <button type="button" className="we-card__art" onClick={onClick}>
        <div className="we-card__poster" style={{ background: film.poster.background }}>
          {film.award && <span className="we-card__badge">{film.award}</span>}
          <div
            className={`we-card__overlay we-card__overlay--${film.poster.overlayFont ?? 'display-italic'}`}
            style={{ color: film.poster.overlayColor ?? 'rgba(255,255,255,0.95)' }}
          >
            {film.poster.overlay}
          </div>
          {film.poster.overlayDecoration === 'vertical-lines' && <DecorVerticalLines />}
          {film.poster.overlayDecoration === 'horizontal-line' && <DecorHorizontalLine />}
        </div>
      </button>
      <div className="we-card__title">{film.title}</div>
      <div className="we-card__meta">{film.director} · {film.year}</div>
      <button type="button" className="we-card__save" onClick={onSave}>
        + Сохранить
      </button>
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

function DecorVerticalLines() {
  return (
    <svg className="we-card__decor" viewBox="0 0 168 160" fill="none" preserveAspectRatio="none" aria-hidden>
      <line x1="50" y1="20" x2="50" y2="140" stroke="rgba(255,255,255,0.25)" strokeWidth="1.2" />
      <line x1="84" y1="20" x2="84" y2="140" stroke="rgba(255,255,255,0.25)" strokeWidth="1.2" />
      <line x1="118" y1="20" x2="118" y2="140" stroke="rgba(255,255,255,0.25)" strokeWidth="1.2" />
    </svg>
  );
}

function DecorHorizontalLine() {
  return (
    <svg className="we-card__decor" viewBox="0 0 168 160" fill="none" preserveAspectRatio="none" aria-hidden>
      <line x1="0" y1="96" x2="168" y2="96" stroke="rgba(255,255,255,0.35)" strokeWidth="1.2" />
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
  color: rgba(233, 217, 167, 0.7);
}

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

.we-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.we-filter {
  height: 28px;
  padding: 0 12px;
  border-radius: 14px;
  border: 1px solid var(--wine-light-border);
  background: var(--color-wine);
  color: rgba(233, 217, 167, 0.85);
  font-family: var(--font-body);
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.we-filter:hover { border-color: rgba(90, 55, 96, 0.7); }
.we-filter.is-active {
  background: var(--gold-tint-strong);
  border-color: var(--gold-border);
  color: var(--color-cream);
  font-weight: 600;
}

.we-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.we-card {
  display: flex;
  flex-direction: column;
}

.we-card__art {
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
  margin-bottom: 10px;
}

.we-card__poster {
  width: 100%;
  aspect-ratio: 168/160;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  padding: 12px;
}

.we-card__badge {
  position: absolute;
  top: 10px;
  left: 10px;
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

.we-card__overlay {
  white-space: pre-line;
  z-index: 1;
}
.we-card__overlay--display-italic {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 400;
  font-size: 30px;
  line-height: 32px;
  letter-spacing: -0.5px;
}
.we-card__overlay--display-bold {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 17px;
  line-height: 20px;
  letter-spacing: 1px;
}
.we-card__overlay--body-caps {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 16px;
  line-height: 18px;
  letter-spacing: 1.5px;
}

.we-card__decor {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.we-card__title {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 15px;
  color: var(--color-cream);
  margin-bottom: 4px;
}

.we-card__meta {
  font-family: var(--font-body);
  font-size: 12px;
  color: rgba(233, 217, 167, 0.6);
  margin-bottom: 10px;
}

.we-card__save {
  height: 32px;
  border-radius: 10px;
  border: 1px solid var(--wine-light-border);
  background: var(--color-wine);
  color: var(--color-cream);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.we-card__save:hover {
  background: var(--color-wine-light);
  border-color: var(--gold-border);
}
`;
