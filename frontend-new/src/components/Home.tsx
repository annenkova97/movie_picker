import { useMemo, useState } from 'react';
import type { Lang } from '../i18n';
import { T } from '../i18n';
import type { Theme } from '../theme';
import type { RecSource, UiMovie } from '../types';
import { buildShelves } from '../shelves';
import { TypoPoster } from './TypoPoster';
import { MoodPicker } from './MoodPicker';
import { QuickAdd } from './QuickAdd';
import { AwardsView } from './AwardsView';

type Tab = 'toWatch' | 'watched' | 'awards';

interface Props {
  th: Theme;
  lang: Lang;
  movies: UiMovie[];
  awards: UiMovie[];
  loading: boolean;
  loadingAwards: boolean;
  adding: boolean;
  picking: boolean;
  addError: string | null;
  savingAwardId: number | null;
  onAdd: (query: string, recSource: RecSource) => Promise<void> | void;
  onPick: (mood: string) => void;
  onMovieClick: (m: UiMovie) => void;
  onToggleWatched: (m: UiMovie) => void;
  onSaveAward: (m: UiMovie, watched: boolean) => void;
}

export function Home(props: Props) {
  const {
    th, lang, movies, awards, loading, loadingAwards, adding, picking,
    addError, savingAwardId, onAdd, onPick, onMovieClick, onToggleWatched, onSaveAward,
  } = props;
  const [tab, setTab] = useState<Tab>('toWatch');
  const [friendMode, setFriendMode] = useState(false);
  const shelves = useMemo(() => buildShelves(movies, lang), [movies, lang]);

  const savedCount = movies.filter((m) => !m.watched).length;
  const watchedCount = movies.filter((m) => m.watched).length;
  const awardsCount = awards.length;

  const dateLabel = new Date().toLocaleDateString(lang === 'ru' ? 'ru-RU' : 'en-US', { weekday: 'long', day: 'numeric', month: 'long' });

  return (
    <div style={{ background: th.bg, minHeight: '100vh', color: th.ink, fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif' }}>
      <div style={{ padding: '28px 40px 40px', display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ fontSize: 11, fontFamily: 'ui-monospace,monospace', color: th.ink3, textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 8 }}>
              {dateLabel} · {savedCount} {T.saved[lang]}
            </div>
            <h1 style={{
              fontFamily: "'Fraunces', 'Playfair Display', Georgia, serif",
              fontWeight: 400, fontStyle: 'italic',
              fontSize: 44, lineHeight: 1.0, letterSpacing: -1,
              margin: 0, color: th.ink,
            } as React.CSSProperties}>
              {lang === 'ru'
                ? <>что посмотрим <span style={{ fontStyle: 'normal', fontWeight: 700 }}>сегодня</span>?</>
                : <>what’s on <span style={{ fontStyle: 'normal', fontWeight: 700 }}>tonight</span>?</>}
            </h1>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          <MoodPicker th={th} lang={lang} onPick={onPick} loading={picking} />
          <QuickAdd th={th} lang={lang} onAdd={onAdd} loading={adding} error={addError} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 4, borderBottom: `1px solid ${th.line}`, marginTop: 4, flexWrap: 'wrap' }}>
          <Tab label={T.toWatch[lang]} count={savedCount} active={tab === 'toWatch'} onClick={() => { setTab('toWatch'); setFriendMode(false); }} th={th} />
          <Tab label={T.watched[lang]} count={watchedCount} active={tab === 'watched'} onClick={() => { setTab('watched'); setFriendMode(false); }} th={th} />
          <Tab label={T.awardsTab[lang]} count={awardsCount} active={tab === 'awards'} onClick={() => { setTab('awards'); setFriendMode(false); }} th={th} />
          <div style={{ flex: 1 }} />
          {tab === 'watched' && watchedCount > 0 && (
            <button onClick={() => setFriendMode(!friendMode)} style={{
              border: `1px solid ${th.line}`, background: friendMode ? th.plum : 'transparent',
              color: friendMode ? th.plumInk : th.ink2,
              padding: '6px 12px', borderRadius: 999, fontSize: 12, cursor: 'pointer', fontWeight: 500,
              marginBottom: 8,
            }}>↗ {T.friendMode[lang]}</button>
          )}
        </div>
      </div>

      {loading && (
        <div style={{ padding: '0 40px 40px', color: th.ink3, fontFamily: 'ui-monospace,monospace', fontSize: 12 }}>
          {T.loading[lang]}
        </div>
      )}

      {!loading && tab === 'toWatch' && (
        savedCount === 0
          ? <Empty th={th} lang={lang} />
          : <Shelves th={th} lang={lang} shelves={shelves} onClick={onMovieClick} />
      )}
      {!loading && tab === 'watched' && (
        friendMode
          ? <FriendView th={th} lang={lang} movies={movies.filter((m) => m.watched)} />
          : <Watched th={th} lang={lang} movies={movies.filter((m) => m.watched)} onToggle={onToggleWatched} />
      )}
      {tab === 'awards' && (
        <AwardsView th={th} lang={lang} movies={awards} loading={loadingAwards} savingId={savingAwardId} onSave={onSaveAward} onOpen={onMovieClick} />
      )}
    </div>
  );
}

function Tab({ label, count, active, onClick, th }: { label: string; count: number; active: boolean; onClick: () => void; th: Theme }) {
  return (
    <button onClick={onClick} style={{
      border: 'none', background: 'transparent', cursor: 'pointer',
      padding: '14px 6px', marginRight: 20, position: 'relative',
      color: active ? th.ink : th.ink3, fontSize: 15, fontWeight: 600,
      fontFamily: "'Fraunces', serif", letterSpacing: -0.2,
      display: 'flex', alignItems: 'baseline', gap: 8,
    }}>
      {label}
      <span style={{ fontSize: 11, fontFamily: 'ui-monospace,monospace', color: th.ink3, fontWeight: 500 }}>{count}</span>
      {active && <div style={{ position: 'absolute', left: 0, right: 0, bottom: -1, height: 2, background: th.plum }} />}
    </button>
  );
}

function Shelves({ th, lang, shelves, onClick }: { th: Theme; lang: Lang; shelves: ReturnType<typeof buildShelves>; onClick: (m: UiMovie) => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 36, paddingBottom: 40 }}>
      {shelves.map((s, idx) => {
        const hero = s.tone === 'hero';
        return (
          <div key={s.id}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, padding: '0 40px', marginBottom: 14, maxWidth: 1200, margin: '0 auto 14px' }}>
              <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: 11, color: th.ink3, letterSpacing: 0.4 }}>
                {String(idx + 1).padStart(2, '0')}
              </span>
              <h2 style={{
                margin: 0, fontFamily: "'Fraunces', serif",
                fontWeight: hero ? 700 : 600, fontSize: hero ? 28 : 20,
                color: th.ink, letterSpacing: -0.4, lineHeight: 1,
              }}>{s.title}</h2>
              <span style={{ fontSize: 12, color: th.ink3, fontFamily: 'ui-monospace,monospace' }}>({s.items.length})</span>
            </div>
            <div style={{
              display: 'flex', gap: hero ? 18 : 12, overflowX: 'auto', overflowY: 'hidden',
              padding: '4px 40px 14px',
              scrollbarWidth: 'thin',
              maxWidth: 1200, margin: '0 auto',
            }}>
              {s.items.map((m) => (
                <PosterCard key={m.id} m={m} th={th} lang={lang} hero={hero}
                  w={hero ? 170 : 130} h={hero ? 255 : 195}
                  onClick={() => onClick(m)} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function PosterCard({ m, th, lang, hero, w, h, onClick }: { m: UiMovie; th: Theme; lang: Lang; hero: boolean; w: number; h: number; onClick: () => void }) {
  const src: Record<RecSource, string> = {
    telegram: '✈ Telegram',
    instagram: '◎ Instagram',
    friends: `♥ ${lang === 'ru' ? 'Друзья' : 'Friends'}`,
    personal: lang === 'ru' ? '• Личное' : '• Personal',
  };
  return (
    <button onClick={onClick} style={{
      border: 'none', background: 'transparent', padding: 0, cursor: 'pointer',
      display: 'flex', flexDirection: 'column', gap: 8, width: w, textAlign: 'left',
      flexShrink: 0,
    }}>
      <TypoPoster movie={m} lang={lang} w={w} h={h} />
      {hero && (
        <div style={{ paddingLeft: 2 }}>
          <div style={{ fontFamily: "'Fraunces',serif", fontWeight: 600, fontSize: 13.5, color: th.ink, lineHeight: 1.15 } as React.CSSProperties}>{m.title}</div>
          <div style={{ fontSize: 10.5, color: th.ink3, marginTop: 2, fontFamily: 'ui-monospace,monospace' }}>{src[m.recSource]} · {m.runtime}{lang === 'ru' ? '' : "'"}</div>
        </div>
      )}
    </button>
  );
}

function Empty({ th, lang }: { th: Theme; lang: Lang }) {
  return (
    <div style={{ padding: '0 40px 40px', display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{
        padding: 32, borderRadius: 20, background: th.bgAlt, border: `1px solid ${th.line}`,
        display: 'flex', gap: 24, alignItems: 'center',
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, fontFamily: 'ui-monospace,monospace', color: th.ink3, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
            ✦ {lang === 'ru' ? 'С чего начать' : 'Where to start'}
          </div>
          <h2 style={{
            margin: 0, fontFamily: "'Fraunces',serif", fontStyle: 'italic',
            fontSize: 30, lineHeight: 1.05, color: th.ink, letterSpacing: -0.6,
          } as React.CSSProperties}>{T.emptyTitle[lang]}</h2>
          <p style={{ fontSize: 14, color: th.ink2, lineHeight: 1.5, margin: '12px 0 0', maxWidth: 520 }}>{T.emptySub[lang]}</p>
        </div>
      </div>
    </div>
  );
}

function Watched({ th, lang, movies, onToggle }: { th: Theme; lang: Lang; movies: UiMovie[]; onToggle: (m: UiMovie) => void }) {
  if (movies.length === 0) {
    return <div style={{ padding: '0 40px 40px', color: th.ink3, fontSize: 13, maxWidth: 1200, margin: '0 auto' }}>—</div>;
  }
  return (
    <div style={{ padding: '0 40px 40px', display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 1200, margin: '0 auto' }}>
      {movies.map((m, i) => (
        <div key={m.id} style={{
          display: 'grid', gridTemplateColumns: '60px 1fr 90px 120px',
          gap: 14, alignItems: 'center',
          padding: '14px 0', borderBottom: i < movies.length - 1 ? `1px solid ${th.line}` : 'none',
        }}>
          <TypoPoster movie={m} lang={lang} w={56} h={84} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: "'Fraunces',serif", fontWeight: 600, fontSize: 15, color: th.ink, lineHeight: 1.15 }}>{m.title}</div>
            <div style={{ fontSize: 11.5, color: th.ink3, marginTop: 3, fontFamily: 'ui-monospace,monospace' }}>{[m.year, m.director].filter(Boolean).join(' · ')}</div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '6px 9px', borderRadius: 8, border: `1px solid ${th.line}`, color: th.ink2, minWidth: 40 }}>
            <div style={{ fontSize: 9, letterSpacing: 0.6, opacity: 0.8, fontFamily: 'ui-monospace,monospace' }}>{T.kp[lang]}</div>
            <div style={{ fontSize: 15, fontWeight: 700, fontFamily: "'Fraunces',serif" }}>{m.publicRating > 0 ? m.publicRating.toFixed(1) : '—'}</div>
          </div>
          <button onClick={() => onToggle(m)} style={{
            border: `1px solid ${th.line}`, background: 'transparent', color: th.ink2,
            padding: '7px 10px', borderRadius: 8, cursor: 'pointer', fontSize: 11.5, fontWeight: 500,
          }}>↺ {T.unwatch[lang]}</button>
        </div>
      ))}
    </div>
  );
}

function FriendView({ th, lang, movies }: { th: Theme; lang: Lang; movies: UiMovie[] }) {
  return (
    <div style={{ padding: '0 40px 40px', display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ fontSize: 11, fontFamily: 'ui-monospace,monospace', color: th.ink3, letterSpacing: 0.6 }}>↗ {T.watchedSub[lang]}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {[...movies].sort((a, b) => b.publicRating - a.publicRating).map((m) => (
          <div key={m.id} style={{
            display: 'flex', gap: 14, padding: 14, borderRadius: 14, background: th.surface,
            border: `1px solid ${th.line}`, alignItems: 'center',
          }}>
            <TypoPoster movie={m} lang={lang} w={60} h={90} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: "'Fraunces',serif", fontWeight: 700, fontSize: 16, color: th.ink, lineHeight: 1.1 }}>{m.title}</div>
              <div style={{ fontSize: 11.5, color: th.ink3, marginTop: 3, fontFamily: 'ui-monospace,monospace' }}>{[m.year, m.director].filter(Boolean).join(' · ')}</div>
              {m.why && <div style={{ fontSize: 12, color: th.ink2, marginTop: 6, fontStyle: 'italic', lineHeight: 1.35 }}>«{m.why}»</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
