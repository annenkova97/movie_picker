/**
 * Lightweight event tracking for the availability experiment.
 *
 * Design rules:
 *  - `track()` MUST never throw — analytics can't break the app.
 *  - Events are buffered and flushed in batches (debounced + on pagehide), so
 *    a burst of events is one request, and the tail isn't lost on navigation.
 *  - A stable `anon_id` (localStorage) stitches guest activity across a session
 *    and into the account after sign-in.
 */
import { sendEvents, type EventPayload } from './api';

export type EventName =
  | 'app_open'
  | 'session_start'
  | 'recommendation_requested'
  | 'tonight_pick_viewed'
  | 'availability_filter_used'
  | 'availability_viewed'
  | 'movie_added'
  | 'marked_watched'
  | 'share_opened'
  | 'launch_clicked';

const ANON_KEY = 'lentochka.anonId';
const FLUSH_DELAY_MS = 2000;
const MAX_BUFFER = 20;

function getAnonId(): string {
  try {
    let id = localStorage.getItem(ANON_KEY);
    if (!id) {
      id =
        (typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `anon-${Date.now()}-${Math.random().toString(36).slice(2)}`);
      localStorage.setItem(ANON_KEY, id);
    }
    return id;
  } catch {
    return 'anon-unknown';
  }
}

let buffer: EventPayload[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;

export function flush(): void {
  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  if (buffer.length === 0) return;
  const batch = buffer;
  buffer = [];
  // Fire-and-forget: swallow any error so callers never see analytics failures.
  void sendEvents(batch).catch(() => {});
}

function scheduleFlush(): void {
  if (flushTimer) return;
  flushTimer = setTimeout(flush, FLUSH_DELAY_MS);
}

export function track(name: EventName, props?: Record<string, unknown>): void {
  try {
    buffer.push({ name, props, anon_id: getAnonId() });
    if (buffer.length >= MAX_BUFFER) flush();
    else scheduleFlush();
  } catch {
    // never break the app on a tracking call
  }
}

// Flush the tail when the tab is hidden / unloaded.
if (typeof window !== 'undefined') {
  window.addEventListener('pagehide', flush);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
}
