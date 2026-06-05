import { useState } from 'react';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import { StarRating } from './StarRating';

export interface DiaryInput {
  rating: number;
  note: string;
}

interface Props {
  lang: Lang;
  initialRating: number;
  initialNote: string;
  onSave: (diary: DiaryInput) => Promise<void> | void;
}

/**
 * Personal diary: 1–5 stars + a free-text note, shown once an item is
 * watched/read. Optional and non-blocking — the user already marked it done;
 * this just captures "how was it" so they don't forget. Reused by MovieDetail
 * and BookDetail. Mount with a key tied to the item id so it resets per item.
 */
export function DiaryEditor({ lang, initialRating, initialNote, onSave }: Props) {
  const [rating, setRating] = useState(initialRating);
  const [note, setNote] = useState(initialNote);
  // Baseline = last saved values; lets us show "Saved ✓" without the parent
  // having to refresh the selected item.
  const [baseRating, setBaseRating] = useState(initialRating);
  const [baseNote, setBaseNote] = useState(initialNote);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const dirty = rating !== baseRating || note.trim() !== baseNote.trim();

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({ rating, note: note.trim() });
      setBaseRating(rating);
      setBaseNote(note.trim());
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="diary">
      <div className="diary__title">{T.diaryTitle[lang]}</div>
      <StarRating value={rating} onChange={(n) => { setRating(n); setSaved(false); }} />
      <textarea
        className="diary__note"
        placeholder={T.diaryNotePh[lang]}
        value={note}
        rows={2}
        onChange={(e) => { setNote(e.target.value); setSaved(false); }}
      />
      <div className="diary__actions">
        <button
          type="button"
          className="diary__save"
          disabled={saving || !dirty}
          onClick={handleSave}
        >
          {saved && !dirty ? T.diarySaved[lang] : T.diarySave[lang]}
        </button>
      </div>
      <style>{styles}</style>
    </div>
  );
}

const styles = `
.diary {
  border-top: 1px solid var(--wine-light-border); padding-top: 16px;
  display: flex; flex-direction: column; gap: 10px;
}
.diary__title {
  font-family: var(--font-body); font-weight: 600; font-size: 10px;
  letter-spacing: 1.2px; text-transform: uppercase; color: var(--color-gold);
}
.diary__note {
  width: 100%; box-sizing: border-box; resize: vertical; min-height: 44px;
  background: var(--color-wine-deep); color: var(--color-cream);
  border: 1px solid var(--wine-light-border); border-radius: 12px;
  padding: 10px 12px; font-family: var(--font-body); font-size: 14px; line-height: 1.5;
}
.diary__note::placeholder { color: var(--cream-55); }
.diary__note:focus { outline: none; border-color: var(--gold-border); }
.diary__actions { display: flex; justify-content: flex-end; }
.diary__save {
  border: 1px solid transparent; padding: 10px 16px; border-radius: 12px;
  font-family: var(--font-body); font-weight: 600; font-size: 13px; cursor: pointer;
  background: var(--color-gold); color: var(--color-wine-deep);
}
.diary__save:disabled { opacity: 0.55; cursor: default; }
`;
