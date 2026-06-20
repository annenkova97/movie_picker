import type { WatchAvailability } from '../api';

/**
 * Renders the subscription (`flatrate`) providers a title is available on, as
 * small gold badges. Shows nothing when there's no flatrate availability — the
 * caller decides whether to render an empty-state instead.
 */
export function ProviderBadges({
  availability,
  max = 4,
}: {
  availability?: WatchAvailability | null;
  max?: number;
}) {
  const flat = availability?.flatrate ?? [];
  if (flat.length === 0) return null;

  const shown = flat.slice(0, max);
  const extra = flat.length - shown.length;

  return (
    <div className="prov-badges">
      {shown.map((p) => (
        <span className="prov-badge" key={p.provider_id}>
          {p.logo_url && (
            <img className="prov-badge__logo" src={p.logo_url} alt="" loading="lazy" />
          )}
          {p.name}
        </span>
      ))}
      {extra > 0 && <span className="prov-badge prov-badge--more">+{extra}</span>}
      {availability?.link && (
        <a
          className="prov-badge__link"
          href={availability.link}
          target="_blank"
          rel="noreferrer noopener"
          aria-label="JustWatch"
          onClick={(e) => e.stopPropagation()}
        >
          ↗
        </a>
      )}
      <style>{styles}</style>
    </div>
  );
}

/** Compact one-line label for a card slot: "Netflix" / "Netflix +1". */
export function streamingLabel(availability?: WatchAvailability | null): string | undefined {
  const names = availability?.flatrate?.map((p) => p.name) ?? [];
  if (names.length === 0) return undefined;
  return names.length === 1 ? names[0] : `${names[0]} +${names.length - 1}`;
}

const styles = `
.prov-badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.prov-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 24px;
  padding: 0 9px;
  border-radius: 6px;
  background: rgba(228, 177, 92, 0.15);
  color: var(--color-gold);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12px;
  white-space: nowrap;
}
.prov-badge--more {
  background: transparent;
  border: 1px solid var(--wine-light-border);
  color: var(--cream-60);
}
.prov-badge__logo {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  object-fit: cover;
}
.prov-badge__link {
  color: var(--cream-60);
  text-decoration: none;
  font-size: 13px;
}
.prov-badge__link:hover { color: var(--color-gold); }
`;
