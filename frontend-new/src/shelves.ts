import type { Lang } from './i18n';
import { T } from './i18n';
import type { UiMovie } from './types';

export interface Shelf {
  id: string;
  title: string;
  items: UiMovie[];
  tone?: 'hero';
}

export function buildShelves(movies: UiMovie[], lang: Lang): Shelf[] {
  const unwatched = movies.filter((m) => !m.watched);
  const byGenre = (g: string) => unwatched.filter((m) => m.genres.includes(g));
  const candidates: Shelf[] = [
    { id: 'today',  title: T.shelfToday[lang],  items: unwatched.slice(0, 8), tone: 'hero' },
    { id: 'recent', title: T.shelfRecent[lang], items: [...unwatched].sort((a, b) => a.savedDaysAgo - b.savedDaysAgo).slice(0, 10) },
    { id: 'drama',  title: T.shelfDrama[lang],  items: byGenre('drama') },
    { id: 'comedy', title: T.shelfComedy[lang], items: byGenre('comedy') },
    { id: 'anim',   title: T.shelfAnim[lang],   items: byGenre('animation') },
    { id: 'thr',    title: T.shelfThr[lang],    items: byGenre('thriller') },
    { id: 'short',  title: T.shelfShort[lang],  items: unwatched.filter((m) => m.runtime <= 100) },
    { id: 'wait',   title: T.shelfWait[lang],   items: unwatched.filter((m) => m.savedDaysAgo >= 30) },
  ];
  return candidates.filter((s) => s.items.length >= 2);
}
