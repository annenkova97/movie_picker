import type { Lang } from '../i18n';
import { T } from '../i18n';
import { bookHue, cleanBookCover, type ApiBook } from '../types';
import { DiaryEditor, type DiaryInput } from './DiaryEditor';

interface Props {
  lang: Lang;
  book: ApiBook | null;
  saving: boolean;
  onClose: () => void;
  onSaveWant?: (b: ApiBook) => void;
  onSaveRead?: (b: ApiBook) => void;
  onToggleRead?: (b: ApiBook) => void;
  onRemove?: (b: ApiBook) => void;
  /** Save personal rating + note for a read, in-library book. */
  onSaveDiary?: (b: ApiBook, diary: DiaryInput) => Promise<void> | void;
}

/** External link target — Google Books for gb: keys, else Open Library. */
function bookExternalLink(workKey: string): { href: string; label: string } {
  if (workKey.startsWith('gb:')) {
    return {
      href: `https://books.google.com/books?id=${encodeURIComponent(workKey.slice(3))}`,
      label: 'Google Books',
    };
  }
  return { href: `https://openlibrary.org/works/${workKey}`, label: 'Open Library' };
}

/** Book detail modal, wine-deep styled. The books analogue of MovieDetail. */
export function BookDetail({
  lang, book, saving, onClose, onSaveWant, onSaveRead, onToggleRead, onRemove, onSaveDiary,
}: Props) {
  if (!book) return null;

  const inLibrary = book.in_library ?? true;
  const cover = cleanBookCover(book.cover_url);
  const authors = book.authors.length ? book.authors.join(' · ') : T.bookAuthorless[lang];
  const meta = [authors, book.year || null].filter(Boolean).join(' · ');
  const hue = bookHue(book);
  const ext = bookExternalLink(book.work_key);

  return (
    <div className="bd-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="bd-card" onClick={(e) => e.stopPropagation()}>
        <div className="bd-head">
          <div className="bd-head__text">
            <h2 className="bd-title">{book.title}</h2>
            <div className="bd-meta">{meta}</div>
          </div>
          <button className="bd-close" onClick={onClose} aria-label={T.settingsClose[lang]}>×</button>
        </div>

        <div className="bd-body">
          <div
            className="bd-cover"
            style={cover
              ? { backgroundImage: `url("${cover}")` }
              : { background: `linear-gradient(160deg, hsl(${hue},45%,38%), hsl(${(hue + 20) % 360},50%,18%))` }}
          >
            {!cover && <span className="bd-cover__title">{book.title}</span>}
          </div>

          <div className="bd-sections">
            <div>
              <div className="bd-section-title">{T.detailPlot[lang]}</div>
              {book.description
                ? <div className="bd-text">{book.description}</div>
                : <div className="bd-text bd-text--empty">{T.detailNoPlot[lang]}</div>}
            </div>

            {book.subjects.length > 0 && (
              <div>
                <div className="bd-section-title">{T.bookSubjects[lang]}</div>
                <div className="bd-chips">
                  {book.subjects.slice(0, 6).map((s) => (
                    <span className="bd-chip" key={s}>{s}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {inLibrary && book.is_read && onSaveDiary && (
          <DiaryEditor
            lang={lang}
            key={book.id}
            initialRating={book.user_rating ?? 0}
            initialNote={book.user_note ?? ''}
            onSave={(diary) => onSaveDiary(book, diary)}
          />
        )}

        <div className="bd-actions">
          {!inLibrary && onSaveWant && (
            <button className="bd-btn bd-btn--primary" onClick={() => onSaveWant(book)} disabled={saving}>
              {T.bookAddWant[lang]}
            </button>
          )}
          {!inLibrary && onSaveRead && (
            <button className="bd-btn bd-btn--ghost" onClick={() => onSaveRead(book)} disabled={saving}>
              {T.bookAddRead[lang]}
            </button>
          )}
          {inLibrary && onToggleRead && (
            <button className="bd-btn bd-btn--ghost" onClick={() => onToggleRead(book)} disabled={saving}>
              {book.is_read ? `↺ ${T.bookBackToList[lang]}` : `✓ ${T.bookMarkRead[lang]}`}
            </button>
          )}
          {inLibrary && onRemove && (
            <button
              className="bd-btn bd-btn--danger"
              disabled={saving}
              onClick={() => {
                const msg = `${T.removeConfirmPrefix[lang]}${book.title}${T.removeConfirmSuffix[lang]}`;
                if (window.confirm(msg)) onRemove(book);
              }}
            >✕ {T.remove[lang]}</button>
          )}
          <span className="bd-spacer" />
          <a
            className="bd-link"
            href={ext.href}
            target="_blank"
            rel="noreferrer noopener"
          >↗ {ext.label}</a>
        </div>

        <style>{styles}</style>
      </div>
    </div>
  );
}

const styles = `
.bd-overlay {
  position: fixed; inset: 0; z-index: 120;
  background: rgba(20, 10, 18, 0.6);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
  padding: 20px; overflow-y: auto;
}
.bd-card {
  background: var(--color-wine); border: 1px solid var(--wine-light-border);
  border-radius: 20px; padding: 26px; max-width: 600px; width: 100%;
  max-height: calc(100vh - 40px); overflow-y: auto;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
  display: flex; flex-direction: column; gap: 18px;
  animation: bd-rise 0.2s ease both;
}
@keyframes bd-rise { from { transform: translateY(12px); opacity: 0; } to { transform: none; opacity: 1; } }
.bd-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.bd-head__text { min-width: 0; }
.bd-title {
  margin: 0; font-family: var(--font-display); font-weight: 700;
  font-size: 26px; line-height: 1.08; letter-spacing: -0.4px; color: var(--color-cream);
}
.bd-meta { margin-top: 8px; font-family: var(--font-body); font-size: 13px; color: var(--cream-60); }
.bd-close { border: none; background: transparent; color: var(--cream-60); font-size: 28px; line-height: 1; cursor: pointer; padding: 0 4px; flex-shrink: 0; }
.bd-body { display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap; }
.bd-cover {
  flex: 0 0 auto; width: 132px; height: 198px; border-radius: 10px;
  background-size: cover; background-position: center;
  box-shadow: 0 12px 24px -12px rgba(0,0,0,0.5);
  display: flex; align-items: flex-end; padding: 10px; overflow: hidden;
}
.bd-cover__title {
  font-family: var(--font-display); font-style: italic; font-weight: 400;
  font-size: 18px; line-height: 1.05; color: rgba(255,255,255,0.95);
}
.bd-sections { flex: 1 1 240px; min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.bd-section-title {
  font-family: var(--font-body); font-weight: 600; font-size: 10px;
  letter-spacing: 1.2px; text-transform: uppercase; color: var(--color-gold); margin-bottom: 6px;
}
.bd-text { font-family: var(--font-body); font-size: 14px; line-height: 1.55; color: var(--cream-85); }
.bd-text--empty { font-style: italic; color: var(--cream-55); }
.bd-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.bd-chip {
  font-family: var(--font-body); font-size: 11px; color: var(--cream-70);
  background: var(--color-wine-deep); border: 1px solid var(--wine-light-border);
  border-radius: 999px; padding: 4px 10px;
}
.bd-actions {
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
  border-top: 1px solid var(--wine-light-border); padding-top: 16px;
}
.bd-btn {
  border: 1px solid transparent; padding: 10px 16px; border-radius: 12px;
  font-family: var(--font-body); font-weight: 600; font-size: 13px; cursor: pointer;
}
.bd-btn:disabled { opacity: 0.6; cursor: wait; }
.bd-btn--primary { background: var(--color-gold); color: var(--color-wine-deep); }
.bd-btn--ghost { background: transparent; border-color: var(--wine-light-border); color: var(--color-cream); }
.bd-btn--ghost:hover:not(:disabled) { border-color: var(--gold-border); }
.bd-btn--danger { background: transparent; border-color: var(--wine-light-border); color: #e08a8a; }
.bd-spacer { flex: 1; }
.bd-link {
  font-family: var(--font-body); font-size: 12px; color: var(--cream-60);
  text-decoration: none; border-bottom: 1px dashed var(--wine-light-border); padding-bottom: 2px;
}
.bd-link:hover { color: var(--color-gold); }
`;
