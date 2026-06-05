import { useState } from 'react';

interface Props {
  /** Current rating 1–5, or null/0 for unrated. */
  value: number | null;
  /** Interactive picker when provided. Click the active top star to clear (0). */
  onChange?: (rating: number) => void;
  /** Star glyph size in px. */
  size?: number;
  /** Read-only renders filled/empty stars with no interaction. */
  readOnly?: boolean;
}

const STARS = [1, 2, 3, 4, 5];

/**
 * 5-star rating, reused by movie and book detail (interactive) and by cards
 * (read-only). Personal "diary" rating — distinct from the public IMDb score.
 */
export function StarRating({ value, onChange, size = 28, readOnly = false }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const current = value ?? 0;
  const interactive = !readOnly && !!onChange;
  const shown = hover ?? current;

  return (
    <div className="sr" role={interactive ? 'radiogroup' : 'img'} aria-label={`${current} / 5`}>
      {STARS.map((n) => {
        const filled = n <= shown;
        const star = (
          <span
            className={`sr-star${filled ? ' sr-star--on' : ''}`}
            style={{ fontSize: size }}
          >
            ★
          </span>
        );
        if (!interactive) return <span key={n}>{star}</span>;
        return (
          <button
            key={n}
            type="button"
            className="sr-btn"
            aria-label={`${n} / 5`}
            aria-checked={current === n}
            role="radio"
            onMouseEnter={() => setHover(n)}
            onMouseLeave={() => setHover(null)}
            onClick={() => onChange!(current === n ? 0 : n)}
          >
            {star}
          </button>
        );
      })}
      <style>{styles}</style>
    </div>
  );
}

const styles = `
.sr { display: inline-flex; align-items: center; gap: 2px; line-height: 1; }
.sr-btn {
  background: none; border: none; padding: 0 1px; cursor: pointer;
  line-height: 1; color: inherit;
}
.sr-star { color: var(--wine-light-border, rgba(255,255,255,0.25)); transition: color 0.12s ease; }
.sr-star--on { color: var(--color-gold, #d8b46a); }
.sr-btn:hover .sr-star { color: var(--color-gold, #d8b46a); }
`;
