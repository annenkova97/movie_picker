import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { UiMovie } from '../types';
import { TypoPoster } from './TypoPoster';
import { DiaryEditor, type DiaryInput } from './DiaryEditor';

interface Props {
  lang: Lang;
  movie: UiMovie | null;
  saving: boolean;
  onClose: () => void;
  onSaveToWatch?: (m: UiMovie) => void;
  onSaveAsWatched?: (m: UiMovie) => void;
  onToggleWatched?: (m: UiMovie) => void;
  onRemove?: (m: UiMovie) => void;
  /** Save personal rating + note for a watched, in-library movie. */
  onSaveDiary?: (m: UiMovie, diary: DiaryInput) => Promise<void> | void;
}

/**
 * Movie detail modal, wine-deep styled. Reused for saved films (library
 * actions: toggle watched / remove) and for award/search results that aren't
 * saved yet (save-to-watch / save-as-watched). Visibility is driven by the
 * `movie` prop being non-null.
 */
export function MovieDetail({
  lang, movie, saving, onClose, onSaveToWatch, onSaveAsWatched, onToggleWatched, onRemove,
  onSaveDiary,
}: Props) {
  if (!movie) return null;

  const meta = [
    movie.director,
    movie.year,
    movie.runtime > 0 ? `${movie.runtime} ${T.min[lang]}` : null,
    movie.publicRating > 0 ? `★ ${movie.publicRating.toFixed(1)}` : null,
  ].filter(Boolean).join(' · ');

  const plot = lang === 'ru'
    ? (movie.plotRu || movie.why || movie.plot)
    : (movie.plot || movie.why);

  return (
    <div className="md-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="md-card" onClick={(e) => e.stopPropagation()}>
        <div className="md-head">
          <div className="md-head__text">
            {movie.award && (
              <div className="md-eyebrow">
                ✦ {movie.award}{movie.awardYear ? ` · ${movie.awardYear}` : ''}
              </div>
            )}
            <h2 className="md-title">{movie.title}</h2>
            <div className="md-meta">{meta}</div>
            {movie.sourceUrl && (
              <a
                className="md-source"
                href={movie.sourceUrl}
                target="_blank"
                rel="noreferrer noopener"
              >
                {movie.recSource === 'instagram'
                  ? `📷 ${T.recSrcInstagram[lang]}`
                  : `📢 ${T.recSrcTelegram[lang]}`} ↗
              </a>
            )}
          </div>
          <button className="md-close" onClick={onClose} aria-label={T.pickClose[lang]}>×</button>
        </div>

        <div className="md-body">
          <TypoPoster movie={movie} lang={lang} w={160} h={240} />
          <div className="md-sections">
            <Section title={T.detailPlot[lang]}>
              {plot
                ? <div className="md-plot">{plot}</div>
                : <div className="md-plot md-plot--empty">{T.detailNoPlot[lang]}</div>}
            </Section>

            {movie.cast.length > 0 && (
              <Section title={T.detailCast[lang]}>
                <div className="md-cast">{movie.cast.slice(0, 6).join(' · ')}</div>
              </Section>
            )}

            {movie.awardsText && !movie.award && (
              <Section title={T.detailAwards[lang]}>
                <div className="md-cast">{movie.awardsText}</div>
              </Section>
            )}
          </div>
        </div>

        {movie.inLibrary && movie.watched && onSaveDiary && (
          <DiaryEditor
            lang={lang}
            key={movie.id}
            initialRating={movie.userRating ?? 0}
            initialNote={movie.userNote ?? ''}
            onSave={(diary) => onSaveDiary(movie, diary)}
          />
        )}

        <div className="md-actions">
          {!movie.inLibrary && onSaveToWatch && (
            <button className="md-btn md-btn--primary" onClick={() => onSaveToWatch(movie)} disabled={saving}>
              {T.addToWatch[lang]}
            </button>
          )}
          {!movie.inLibrary && onSaveAsWatched && (
            <button className="md-btn md-btn--ghost" onClick={() => onSaveAsWatched(movie)} disabled={saving}>
              {T.addToWatched[lang]}
            </button>
          )}
          {movie.inLibrary && onToggleWatched && (
            <button className="md-btn md-btn--ghost" onClick={() => onToggleWatched(movie)} disabled={saving}>
              {movie.watched ? `↺ ${T.unwatch[lang]}` : `✓ ${T.markWatched[lang]}`}
            </button>
          )}
          {movie.inLibrary && onRemove && (
            <button
              className="md-btn md-btn--danger"
              disabled={saving}
              onClick={() => {
                const msg = `${T.removeConfirmPrefix[lang]}${movie.title}${T.removeConfirmSuffix[lang]}`;
                if (window.confirm(msg)) onRemove(movie);
              }}
            >✕ {T.remove[lang]}</button>
          )}

          <span className="md-spacer" />

          <a
            className="md-imdb"
            href={`https://www.imdb.com/title/${movie.imdbId}/`}
            target="_blank"
            rel="noreferrer noopener"
          >↗ {T.detailImdb[lang]}</a>
        </div>

        <style>{styles}</style>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="md-section-title">{title}</div>
      {children}
    </div>
  );
}

const styles = `
.md-overlay {
  position: fixed; inset: 0; z-index: 120;
  background: rgba(20, 10, 18, 0.6);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
  padding: 20px; overflow-y: auto;
}
.md-card {
  background: var(--color-wine);
  border: 1px solid var(--wine-light-border);
  border-radius: 20px; padding: 26px;
  max-width: 640px; width: 100%;
  max-height: calc(100vh - 40px); overflow-y: auto;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
  display: flex; flex-direction: column; gap: 18px;
  animation: md-rise 0.2s ease both;
}
@keyframes md-rise { from { transform: translateY(12px); opacity: 0; } to { transform: none; opacity: 1; } }
.md-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.md-head__text { min-width: 0; }
.md-eyebrow {
  font-family: var(--font-body); font-weight: 600; font-size: 10px;
  letter-spacing: 1.4px; text-transform: uppercase; color: var(--color-gold);
}
.md-title {
  margin: 6px 0 0; font-family: var(--font-display); font-weight: 700;
  font-size: 28px; line-height: 1.06; letter-spacing: -0.4px; color: var(--color-cream);
}
.md-meta {
  margin-top: 8px; font-family: var(--font-body); font-size: 13px; color: var(--cream-60);
}
.md-source {
  display: inline-block; margin-top: 6px; font-family: var(--font-body);
  font-size: 12px; color: var(--color-gold); text-decoration: underline;
  text-underline-offset: 2px;
}
.md-close {
  border: none; background: transparent; color: var(--cream-60);
  font-size: 28px; line-height: 1; cursor: pointer; padding: 0 4px; flex-shrink: 0;
}
.md-body { display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap; }
.md-sections { flex: 1 1 260px; min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.md-section-title {
  font-family: var(--font-body); font-weight: 600; font-size: 10px;
  letter-spacing: 1.2px; text-transform: uppercase; color: var(--color-gold); margin-bottom: 6px;
}
.md-plot { font-family: var(--font-body); font-size: 14px; line-height: 1.55; color: var(--cream-85); }
.md-plot--empty { font-style: italic; color: var(--cream-55); }
.md-cast { font-family: var(--font-body); font-size: 13px; line-height: 1.45; color: var(--cream-70); }
.md-actions {
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
  border-top: 1px solid var(--wine-light-border); padding-top: 16px;
}
.md-btn {
  border: 1px solid transparent; padding: 10px 16px; border-radius: 12px;
  font-family: var(--font-body); font-weight: 600; font-size: 13px; cursor: pointer;
  transition: filter 0.15s ease, background 0.15s ease;
}
.md-btn:disabled { opacity: 0.6; cursor: wait; }
.md-btn--primary { background: var(--color-gold); color: var(--color-wine-deep); }
.md-btn--primary:hover:not(:disabled) { filter: brightness(1.07); }
.md-btn--ghost { background: transparent; border-color: var(--wine-light-border); color: var(--color-cream); }
.md-btn--ghost:hover:not(:disabled) { border-color: var(--gold-border); }
.md-btn--danger { background: transparent; border-color: var(--wine-light-border); color: #e08a8a; }
.md-btn--danger:hover:not(:disabled) { border-color: rgba(224, 138, 138, 0.5); }
.md-spacer { flex: 1; }
.md-imdb {
  font-family: var(--font-body); font-size: 12px; color: var(--cream-60);
  text-decoration: none; border-bottom: 1px dashed var(--wine-light-border); padding-bottom: 2px;
}
.md-imdb:hover { color: var(--color-gold); }
`;
