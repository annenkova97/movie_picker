import { useMemo, useState } from 'react';
import { useSettings } from '../../settings';
import { T } from '../../i18n';
import { useBooks } from '../../hooks/useBooks';
import { recommendBooks } from '../../api';
import { bookHue, cleanBookCover, type ApiBook } from '../../types';
import { BookDetail } from '../BookDetail';
import { BookSearchSheet } from '../BookSearchSheet';

interface Props {
  onBack: () => void;
}

/** Full-screen books experience: reading shelves, search, and a mood pick. */
export function BooksScreen({ onBack }: Props) {
  const { lang } = useSettings();
  const books = useBooks();
  const all = books.list.data ?? [];

  const want = useMemo(() => all.filter((b) => !b.is_read), [all]);
  const read = useMemo(() => all.filter((b) => b.is_read), [all]);

  const [searchOpen, setSearchOpen] = useState(false);
  const [selected, setSelected] = useState<ApiBook | null>(null);
  const [mood, setMood] = useState('');
  const [picking, setPicking] = useState(false);
  const [picks, setPicks] = useState<ApiBook[] | null>(null);
  const [pickNote, setPickNote] = useState<string | null>(null);

  const detailSaving = books.patch.isPending || books.remove.isPending;

  const runPick = async () => {
    const q = mood.trim();
    if (!q) return;
    setPicking(true);
    setPickNote(null);
    try {
      const inline = books.isGuest ? all : undefined;
      const res = await recommendBooks(q, false, inline);
      setPicks(res.books);
      setPickNote(res.explanation);
    } catch (e) {
      setPickNote(e instanceof Error ? e.message : String(e));
    } finally {
      setPicking(false);
    }
  };

  if (searchOpen) {
    return <BookSearchSheet onClose={() => setSearchOpen(false)} />;
  }

  const isEmpty = all.length === 0;

  return (
    <div className="lt-screen bk-screen">
      <header className="bk-header">
        <button className="bk-back" onClick={onBack} aria-label={T.back[lang]}>←</button>
        <div className="bk-head-text">
          <div className="bk-eyebrow">{T.booksSubtitle[lang]}</div>
          <h1 className="bk-title">{T.booksTitle[lang]}</h1>
        </div>
        <button className="bk-search" onClick={() => setSearchOpen(true)}>
          {T.booksFindCta[lang]}
        </button>
      </header>

      {isEmpty ? (
        <section className="bk-empty">
          <div className="bk-empty__title">{T.booksEmptyTitle[lang]} <span aria-hidden>📚</span></div>
          <div className="bk-empty__sub">{T.booksEmptySub[lang]}</div>
          <button className="bk-empty__cta" onClick={() => setSearchOpen(true)}>
            {T.booksFindCta[lang]} →
          </button>
        </section>
      ) : (
        <>
          <section className="bk-pick">
            <input
              className="bk-pick__input"
              value={mood}
              onChange={(e) => setMood(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') runPick(); }}
              placeholder={T.pickBookPh[lang]}
            />
            <button className="bk-pick__btn" onClick={runPick} disabled={picking || !mood.trim()}>
              {picking ? '…' : T.pickBookGo[lang]}
            </button>
          </section>

          {picks && picks.length > 0 && (
            <section className="bk-shelf">
              <div className="bk-shelf__title">{T.pickBookCta[lang]}</div>
              {pickNote && <div className="bk-note">{pickNote}</div>}
              <div className="bk-list">
                {picks.map((b) => (
                  <BookRow key={`pick-${b.id}`} book={b} lang={lang} onClick={() => setSelected(b)} />
                ))}
              </div>
            </section>
          )}

          {want.length > 0 && (
            <Shelf title={T.booksWantToRead[lang]} books={want} lang={lang} onSelect={setSelected} />
          )}
          {read.length > 0 && (
            <Shelf title={T.booksRead[lang]} books={read} lang={lang} onSelect={setSelected} />
          )}
        </>
      )}

      <BookDetail
        lang={lang}
        book={selected}
        saving={detailSaving}
        onClose={() => setSelected(null)}
        onToggleRead={(b) =>
          books.patch.mutateAsync({ id: b.id, fields: { is_read: !b.is_read } }).finally(() => setSelected(null))}
        onRemove={(b) => books.remove.mutateAsync(b.id).finally(() => setSelected(null))}
      />

      <style>{styles}</style>
    </div>
  );
}

function Shelf({ title, books, lang, onSelect }: {
  title: string; books: ApiBook[]; lang: 'ru' | 'en'; onSelect: (b: ApiBook) => void;
}) {
  return (
    <section className="bk-shelf">
      <div className="bk-shelf__title">{title} <span className="bk-shelf__count">{books.length}</span></div>
      <div className="bk-list">
        {books.map((b) => (
          <BookRow key={b.id} book={b} lang={lang} onClick={() => onSelect(b)} />
        ))}
      </div>
    </section>
  );
}

function BookRow({ book, lang, onClick }: { book: ApiBook; lang: 'ru' | 'en'; onClick: () => void }) {
  const cover = cleanBookCover(book.cover_url);
  const hue = bookHue(book);
  const author = book.authors.length ? book.authors.join(', ') : T.bookAuthorless[lang];
  return (
    <button className="bk-card" onClick={onClick}>
      <div
        className="bk-card__cover"
        style={cover
          ? { backgroundImage: `url("${cover}")` }
          : { background: `linear-gradient(160deg, hsl(${hue},45%,38%), hsl(${(hue + 20) % 360},50%,18%))` }}
      />
      <div className="bk-card__text">
        <div className="bk-card__title">{book.title}</div>
        <div className="bk-card__meta">{[author, book.year || null].filter(Boolean).join(' · ')}</div>
      </div>
      {book.is_read && <span className="bk-card__badge">✓</span>}
    </button>
  );
}

const styles = `
.bk-header {
  display: flex; align-items: center; gap: 12px;
  max-width: 390px; margin: 0 auto; padding: 56px 20px 0;
}
.bk-back {
  width: 40px; height: 40px; border-radius: 50%;
  background: var(--color-wine); border: 1px solid var(--wine-light-border);
  color: var(--color-cream); font-size: 20px; cursor: pointer; flex: 0 0 auto;
}
.bk-back:hover { background: var(--color-wine-light); }
.bk-head-text { flex: 1; min-width: 0; }
.bk-eyebrow {
  font-family: var(--font-body); font-weight: 600; font-size: 11px;
  letter-spacing: 1.4px; color: var(--color-gold); margin-bottom: 4px;
}
.bk-title {
  font-family: var(--font-display); font-weight: 700; font-size: 26px;
  letter-spacing: -0.4px; color: var(--color-cream); margin: 0;
}
.bk-search {
  flex: 0 0 auto; height: 36px; padding: 0 14px; border-radius: 999px;
  border: 1px solid var(--gold-border); background: var(--gold-tint-strong);
  color: var(--color-cream); font-family: var(--font-body); font-weight: 600;
  font-size: 13px; cursor: pointer; white-space: nowrap;
}
.bk-empty {
  max-width: 390px; margin: 40px auto 0; padding: 24px 20px;
  text-align: center;
}
.bk-empty__title { font-family: var(--font-display); font-weight: 700; font-size: 22px; color: var(--color-cream); }
.bk-empty__sub { font-family: var(--font-body); font-size: 14px; color: var(--cream-70); margin: 10px 0 20px; line-height: 1.5; }
.bk-empty__cta {
  height: 44px; padding: 0 22px; border-radius: 14px; border: none;
  background: var(--color-gold); color: var(--color-wine-deep);
  font-family: var(--font-body); font-weight: 600; font-size: 15px; cursor: pointer;
}
.bk-pick {
  max-width: 390px; margin: 22px auto 0; padding: 0 20px; display: flex; gap: 8px;
}
.bk-pick__input {
  flex: 1; min-width: 0; height: 44px; padding: 0 16px; border-radius: 12px;
  border: 1px solid var(--wine-light-border); background: var(--color-wine);
  color: var(--color-cream); font-family: var(--font-body); font-size: 14px; outline: none;
}
.bk-pick__input:focus { border-color: var(--gold-border); }
.bk-pick__btn {
  height: 44px; padding: 0 18px; border-radius: 12px; border: 1px solid var(--gold-border);
  background: var(--gold-tint-strong); color: var(--color-cream);
  font-family: var(--font-body); font-weight: 600; font-size: 14px; cursor: pointer;
}
.bk-pick__btn:disabled { opacity: 0.6; cursor: default; }
.bk-shelf { max-width: 390px; margin: 28px auto 0; padding: 0 20px; }
.bk-shelf:last-of-type { padding-bottom: 48px; }
.bk-shelf__title {
  font-family: var(--font-body); font-weight: 600; font-size: 16px;
  color: var(--color-cream); margin-bottom: 12px;
}
.bk-shelf__count { color: var(--cream-50); font-size: 13px; margin-left: 4px; }
.bk-note { font-family: var(--font-display); font-style: italic; font-size: 13px; color: var(--cream-85); margin-bottom: 12px; line-height: 1.45; }
.bk-list { display: flex; flex-direction: column; gap: 10px; }
.bk-card {
  display: flex; align-items: center; gap: 12px; width: 100%; text-align: left;
  background: var(--color-wine); border: 1px solid var(--wine-light-border);
  border-radius: 14px; padding: 10px; cursor: pointer; position: relative;
}
.bk-card:hover { border-color: var(--gold-border); }
.bk-card__cover {
  width: 44px; height: 64px; border-radius: 8px; flex: 0 0 auto;
  background-size: cover; background-position: center; background-color: var(--color-wine-deep);
}
.bk-card__text { flex: 1; min-width: 0; }
.bk-card__title {
  font-family: var(--font-display); font-weight: 700; font-size: 16px;
  color: var(--color-cream); line-height: 1.2;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bk-card__meta {
  font-family: var(--font-body); font-size: 12px; color: var(--cream-60); margin-top: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bk-card__badge {
  flex: 0 0 auto; width: 22px; height: 22px; border-radius: 50%;
  background: var(--gold-tint-strong); color: var(--color-gold);
  display: inline-flex; align-items: center; justify-content: center; font-size: 12px;
}
`;
