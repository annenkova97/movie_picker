import { useSettings } from '../../settings';
import { T } from '../../i18n';
import type { RecFilm } from './WatchlistMain';
import { CuratedGrid } from './CuratedGrid';

interface Props {
  curated: RecFilm[];
  onBack: () => void;
  onSave: (film: RecFilm) => void;
  onSelect: (film: RecFilm) => void;
}

/** Full-screen browse of all award-winning films, opened from "Все →". */
export function AwardsBrowse({ curated, onBack, onSave, onSelect }: Props) {
  const { lang } = useSettings();

  return (
    <div className="lt-screen ab-screen">
      <header className="ab-header">
        <button className="ab-back" onClick={onBack} aria-label={T.back[lang]}>←</button>
        <div>
          <div className="ab-eyebrow">{T.wlRecsEyebrow[lang]}</div>
          <h1 className="ab-title">{T.wlRecsTitle[lang]}</h1>
        </div>
      </header>

      <section className="ab-body">
        <CuratedGrid
          curated={curated}
          saveLabel={T.addToWatch[lang]}
          allLabel={T.wlFilterAll[lang]}
          onSave={onSave}
          onSelect={onSelect}
        />
      </section>

      <style>{styles}</style>
    </div>
  );
}

const styles = `
.ab-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 390px;
  margin: 0 auto;
  padding: 56px 20px 0;
}
.ab-back {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-wine);
  border: 1px solid var(--wine-light-border);
  color: var(--color-cream);
  font-size: 20px;
  cursor: pointer;
  flex: 0 0 auto;
}
.ab-back:hover { background: var(--color-wine-light); }
.ab-eyebrow {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 2.4px;
  text-transform: uppercase;
  color: var(--color-gold);
  margin-bottom: 4px;
}
.ab-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 26px;
  letter-spacing: -0.4px;
  color: var(--color-cream);
  margin: 0;
}
.ab-body {
  max-width: 390px;
  margin: 24px auto 0;
  padding: 0 20px 48px;
}
`;
