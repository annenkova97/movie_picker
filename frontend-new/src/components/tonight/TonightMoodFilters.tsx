import { useEffect, useState } from 'react';

interface FilterGroup {
  key: string;
  label: string;
  options: string[];
}

interface Props {
  open: boolean;
  loading?: boolean;
  onClose: () => void;
  onSubmit: (payload: { text: string; genre: string | null; duration: string | null; era: string | null }) => void;
}

const SUGGESTIONS = ['поплакать', 'классика', 'с друзьями', 'романтичный вечер', 'что-то странное'];

const FILTER_GROUPS: FilterGroup[] = [
  {
    key: 'genre',
    label: 'Жанр',
    options: ['Любой', 'Комедия', 'Драма', 'Триллер', 'Фантастика', 'Документалка', 'Мелодрама', 'Ужасы', 'Анимация'],
  },
  {
    key: 'duration',
    label: 'Длительность',
    options: ['Любой', 'До 90 мин', '90–120 мин', 'Больше 2 часов'],
  },
  {
    key: 'era',
    label: 'Эпоха',
    options: ['Любой', '2020-е', '2010-е', '2000-е', '90-е', 'Старое кино'],
  },
];

const PLACEHOLDER = 'лёгкое, ламповое, под пиццу...';

export function TonightMoodFilters({ open, loading = false, onClose, onSubmit }: Props) {
  const [text, setText] = useState('');
  const [genre, setGenre] = useState<string>('Любой');
  const [duration, setDuration] = useState<string>('Любой');
  const [era, setEra] = useState<string>('Любой');

  // Lock body scroll while modal open
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  // Escape closes
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = () => {
    if (loading) return;
    onSubmit({
      text: text.trim(),
      genre: genre === 'Любой' ? null : genre,
      duration: duration === 'Любой' ? null : duration,
      era: era === 'Любой' ? null : era,
    });
  };

  const setForGroup = (key: string, value: string) => {
    if (key === 'genre') setGenre(value);
    if (key === 'duration') setDuration(value);
    if (key === 'era') setEra(value);
  };

  const valueForGroup = (key: string) => {
    if (key === 'genre') return genre;
    if (key === 'duration') return duration;
    return era;
  };

  return (
    <div className="lt-screen" role="dialog" aria-modal="true" aria-label="Какое настроение?">
      <StarField />

      <button className="lt-close" onClick={onClose} aria-label="Закрыть">
        <CloseIcon />
      </button>

      <div className="lt-screen__inner">
        <h1 className="lt-title">Какое настроение?</h1>

        <MoodInputPill
          value={text}
          loading={loading}
          onChange={setText}
          onSubmit={handleSubmit}
        />

        <div className="lt-suggestions">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              className="lt-chip lt-chip--suggestion"
              onClick={() => setText(s)}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="lt-divider" />

        {FILTER_GROUPS.map((group) => (
          <FilterSection
            key={group.key}
            eyebrow={group.label}
            options={group.options}
            value={valueForGroup(group.key)}
            onSelect={(v) => setForGroup(group.key, v)}
          />
        ))}
      </div>

      <style>{styles}</style>
    </div>
  );
}

function MoodInputPill({
  value, loading, onChange, onSubmit,
}: {
  value: string;
  loading: boolean;
  onChange: (v: string) => void;
  onSubmit: () => void;
}) {
  return (
    <div className="lt-mood-pill">
      <textarea
        className="lt-mood-pill__input"
        value={value}
        rows={2}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          // Enter submits; Shift+Enter inserts newline.
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSubmit();
          }
        }}
        placeholder={PLACEHOLDER}
        aria-label="Опиши настроение"
      />
      <button
        className="lt-mood-pill__cta"
        type="button"
        onClick={onSubmit}
        disabled={loading}
      >
        {loading ? '…' : 'Подобрать →'}
      </button>
    </div>
  );
}

function FilterSection({
  eyebrow, options, value, onSelect,
}: {
  eyebrow: string;
  options: string[];
  value: string;
  onSelect: (v: string) => void;
}) {
  return (
    <section className="lt-filter-section">
      <div className="lt-eyebrow">{eyebrow}</div>
      <div className="lt-chip-row">
        {options.map((opt) => {
          const active = opt === value;
          return (
            <button
              key={opt}
              type="button"
              className={`lt-chip lt-chip--filter${active ? ' is-active' : ''}`}
              onClick={() => onSelect(opt)}
              aria-pressed={active}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function CloseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

function StarField() {
  // A few subtle decorative dots in the upper negative space.
  const stars = [
    { x: '14%', y: '7%', r: 1.4, o: 0.55 },
    { x: '50%', y: '11%', r: 1.0, o: 0.40 },
    { x: '76%', y: '5%', r: 1.2, o: 0.45 },
    { x: '88%', y: '15%', r: 1.0, o: 0.35 },
    { x: '32%', y: '17%', r: 1.0, o: 0.42 },
  ];
  return (
    <div className="lt-stars" aria-hidden>
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

const styles = `
.lt-screen__inner {
  max-width: 390px;
  margin: 0 auto;
  padding: 96px 20px 56px;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

.lt-stars {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  max-width: 390px;
  left: 50%;
  transform: translateX(-50%);
  height: 260px;
}
.lt-stars > span {
  position: absolute;
  border-radius: 50%;
  background: var(--color-cream);
  display: block;
}

.lt-close {
  position: absolute;
  top: 56px;
  left: 50%;
  transform: translateX(155px); /* 390/2 - 40 - 4 = 151, button half offset → keep right-edge ~ x=334 */
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
.lt-close:hover { background: var(--color-wine-light); }
.lt-close:focus-visible {
  outline: 2px solid var(--gold-border-strong);
  outline-offset: 2px;
}

.lt-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 40px;
  line-height: 46px;
  letter-spacing: -1.5px;
  color: var(--color-cream);
  margin: 0 0 28px;
}

.lt-mood-pill {
  display: flex;
  align-items: center;
  width: 100%;
  height: 56px;
  background: var(--color-wine);
  border: 1px solid var(--wine-light-border);
  border-radius: var(--radius-pill);
  padding: 6px;
  position: relative;
}
.lt-mood-pill__input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-cream);
  font-size: 15px;
  padding: 8px 8px 8px 18px;
  font-family: inherit;
  line-height: 18px;
  resize: none;
  overflow: hidden;
}
.lt-mood-pill__input::placeholder {
  color: var(--color-cream-soft);
  opacity: 0.55;
}
.lt-mood-pill__cta {
  flex: 0 0 auto;
  height: 44px;
  padding: 0 18px;
  min-width: 128px;
  background: var(--color-gold);
  color: var(--color-wine-deep);
  border: 0;
  border-radius: 22px;
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0;
  cursor: pointer;
  transition: background 0.15s ease;
}
.lt-mood-pill__cta:hover { background: var(--color-gold-dark); }
.lt-mood-pill__cta:disabled {
  cursor: wait;
  opacity: 0.7;
}
.lt-mood-pill__cta:focus-visible {
  outline: 2px solid var(--color-cream);
  outline-offset: 3px;
}

.lt-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 28px;
}

.lt-chip {
  height: 32px;
  display: inline-flex;
  align-items: center;
  /* Spec is padding 0 14, but at 14 the four-chip row 1 of ЖАНР (Любой /
     Комедия / Драма / Триллер) overflows the 350-wide content column at
     our Inter font metrics. Trimming to 11 keeps the design's 4-3-2 row
     packing exactly. */
  padding: 0 11px;
  border-radius: 16px;
  border: 1px solid var(--wine-light-border);
  background: var(--color-wine);
  color: var(--color-cream-soft);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 400;
  letter-spacing: -0.1px;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}
.lt-chip:hover { border-color: rgba(90, 55, 96, 0.7); }
.lt-chip:focus-visible {
  outline: 2px solid var(--gold-border-strong);
  outline-offset: 2px;
}

.lt-chip--suggestion {
  height: 30px;
  padding: 0 14px;
  border-radius: 15px;
  font-size: 13px;
  color: rgba(233, 217, 167, 0.9); /* cream-soft 90% */
  border-color: rgba(90, 55, 96, 0.45);
}

.lt-chip--filter {
  height: 32px;
  font-size: 14px;
  color: rgba(245, 230, 184, 0.85); /* cream 85% — slightly more legible than cream-soft */
  border-color: rgba(90, 55, 96, 0.45);
}
.lt-chip--filter.is-active {
  background: var(--color-cream);
  color: var(--color-wine-deep);
  border-color: var(--color-cream);
  font-weight: 600;
}
.lt-chip--filter.is-active:hover { background: var(--color-cream); }

.lt-divider {
  height: 1px;
  background: rgba(90, 55, 96, 0.30);
  margin: 30px 0 28px;
}

.lt-filter-section + .lt-filter-section {
  margin-top: 24px;
}

.lt-eyebrow {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 2.8px;
  text-transform: uppercase;
  color: var(--color-gold);
  margin-bottom: 16px;
}

.lt-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 8px;
}

@media (max-width: 420px) {
  .lt-close { transform: none; left: auto; right: 16px; }
}
`;
