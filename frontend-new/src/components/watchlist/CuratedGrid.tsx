import { useState } from 'react';
import type { RecFilm } from './WatchlistMain';

/**
 * Award filter chips + 2-column grid of curated/award cards. Shared by the
 * empty state and the full "see all awards" browse screen so the card markup,
 * filter logic, and styles live in exactly one place.
 */

export type AwardFilter = 'all' | 'oscar' | 'palme' | 'golden-globe';

const FILTER_LABELS: { key: AwardFilter; label: string }[] = [
  { key: 'all', label: 'Все' },
  { key: 'oscar', label: 'Oscar' },
  { key: 'palme', label: "Palme d'Or" },
  { key: 'golden-globe', label: 'Golden Globe' },
];

const AWARD_KEYS: Record<AwardFilter, (award?: string) => boolean> = {
  all: () => true,
  oscar: (a) => !!a && /oscar/i.test(a),
  palme: (a) => !!a && /palme|cannes/i.test(a),
  'golden-globe': (a) => !!a && /golden globe/i.test(a),
};

interface Props {
  curated: RecFilm[];
  saveLabel: string;
  /** Localized label for the "All" filter chip. */
  allLabel: string;
  onSave: (film: RecFilm) => void;
  onSelect: (film: RecFilm) => void;
}

export function CuratedGrid({ curated, saveLabel, allLabel, onSave, onSelect }: Props) {
  const [filter, setFilter] = useState<AwardFilter>('all');
  const films = curated.filter((f) => AWARD_KEYS[filter](f.award));

  return (
    <>
      <div className="we-filters">
        {FILTER_LABELS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={`we-filter${filter === key ? ' is-active' : ''}`}
            onClick={() => setFilter(key)}
            aria-pressed={filter === key}
          >
            {key === 'all' ? allLabel : label}
          </button>
        ))}
      </div>

      <div className="we-grid">
        {films.map((film) => (
          <CuratedCard
            key={film.id}
            film={film}
            saveLabel={saveLabel}
            onSave={() => onSave(film)}
            onClick={() => onSelect(film)}
          />
        ))}
      </div>

      <style>{styles}</style>
    </>
  );
}

function CuratedCard({
  film, saveLabel, onSave, onClick,
}: {
  film: RecFilm;
  saveLabel: string;
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
        {saveLabel}
      </button>
    </div>
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

const styles = `
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
  color: var(--cream-85);
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
  color: var(--cream-60);
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
