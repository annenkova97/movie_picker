/**
 * Book library abstraction — the books analogue of library.ts.
 *
 *   - BackendBookLibrary: authenticated user → /api/books/*.
 *   - LocalBookLibrary: guest → localStorage, no auth.
 *
 * Components consume useBooks() and never branch on auth state directly.
 */

import type { ApiBook } from './types';
import type { BookPatch } from './api';
import {
  addBookByKey,
  addBookByQuery,
  bulkImportBooks,
  deleteBook,
  getBookPreview,
  listBooks,
  patchBook,
  searchBooks,
} from './api';

const LOCAL_STORAGE_KEY = 'lentochka.books.v1';
const LOCAL_MAX_RECORDS = 2000;

export class LocalBookLibraryFullError extends Error {
  constructor() {
    super('Local book library is full. Sign up to keep saving.');
    this.name = 'LocalBookLibraryFullError';
  }
}

function readLocal(): ApiBook[] {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeLocal(books: ApiBook[]): void {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(books));
  } catch (e) {
    console.warn('[bookLibrary] failed to persist', e);
  }
}

function syntheticId(workKey: string): number {
  let h = 5381;
  for (let i = 0; i < workKey.length; i++) {
    h = ((h << 5) + h + workKey.charCodeAt(i)) >>> 0;
  }
  return h & 0x7fffffff;
}

function nowIso(): string {
  return new Date().toISOString();
}

function previewToApiBook(
  preview: Awaited<ReturnType<typeof getBookPreview>>,
  isRead: boolean,
): ApiBook {
  return {
    id: syntheticId(preview.work_key),
    work_key: preview.work_key,
    title: preview.title,
    authors: preview.authors ?? [],
    year: preview.year,
    subjects: preview.subjects ?? [],
    description: preview.description,
    cover_url: preview.cover_url,
    rating: preview.rating,
    is_read: isRead,
    source: 'personal',
    rec_source: 'personal',
    rec_note: null,
    in_library: true,
    added_at: nowIso(),
  };
}

export interface BookLibrary {
  readonly isGuest: boolean;
  list(): Promise<ApiBook[]>;
  saveByWorkKey(workKey: string, isRead: boolean): Promise<ApiBook>;
  addByQuery(query: string): Promise<ApiBook>;
  patch(id: number, fields: BookPatch): Promise<ApiBook>;
  remove(id: number): Promise<void>;
}

class BackendBookLibrary implements BookLibrary {
  readonly isGuest = false;

  list() {
    return listBooks();
  }

  async saveByWorkKey(workKey: string, isRead: boolean): Promise<ApiBook> {
    const saved = await addBookByKey(workKey);
    if (isRead && saved.id) return patchBook(saved.id, { is_read: true });
    return saved;
  }

  addByQuery(query: string) {
    return addBookByQuery(query);
  }

  patch(id: number, fields: BookPatch) {
    return patchBook(id, fields);
  }

  remove(id: number) {
    return deleteBook(id);
  }
}

class LocalBookLibrary implements BookLibrary {
  readonly isGuest = true;

  async list(): Promise<ApiBook[]> {
    return readLocal();
  }

  async saveByWorkKey(workKey: string, isRead: boolean): Promise<ApiBook> {
    const all = readLocal();
    const existing = all.find((b) => b.work_key === workKey);
    if (existing) {
      if (existing.is_read !== isRead) {
        existing.is_read = isRead;
        writeLocal(all);
      }
      return existing;
    }
    if (all.length >= LOCAL_MAX_RECORDS) throw new LocalBookLibraryFullError();
    const preview = await getBookPreview(workKey);
    const record = previewToApiBook(preview, isRead);
    all.push(record);
    writeLocal(all);
    return record;
  }

  async addByQuery(query: string): Promise<ApiBook> {
    const trimmed = query.trim();
    if (/^OL\d+W$/i.test(trimmed)) return this.saveByWorkKey(trimmed, false);
    const results = await searchBooks(trimmed);
    if (results.length === 0) throw new Error('Nothing matches');
    return this.saveByWorkKey(results[0].work_key, false);
  }

  async patch(id: number, fields: BookPatch): Promise<ApiBook> {
    const all = readLocal();
    const book = all.find((b) => b.id === id);
    if (!book) throw new Error('Book not found in local library');
    if (fields.is_read !== undefined) {
      book.is_read = fields.is_read;
      if (fields.is_read && !book.read_at) book.read_at = nowIso();
    }
    if (fields.user_rating !== undefined) {
      book.user_rating = fields.user_rating && fields.user_rating > 0 ? fields.user_rating : null;
    }
    if (fields.user_note !== undefined) book.user_note = fields.user_note || null;
    writeLocal(all);
    return book;
  }

  async remove(id: number): Promise<void> {
    const all = readLocal();
    const next = all.filter((b) => b.id !== id);
    if (next.length === all.length) throw new Error('Book not found in local library');
    writeLocal(next);
  }
}

const _backend = new BackendBookLibrary();
const _local = new LocalBookLibrary();

export function getBookLibrary(isGuest: boolean): BookLibrary {
  return isGuest ? _local : _backend;
}

/**
 * Drains the local guest book library into the authenticated account after
 * login/register. Mirrors migrateGuestLibrary() for movies. Idempotent on
 * (user_id, work_key); the local copy is kept on failure.
 */
export async function migrateGuestBooks(): Promise<number> {
  const local = readLocal();
  if (local.length === 0) return 0;
  await bulkImportBooks(
    local.map((b) => ({
      work_key: b.work_key,
      is_read: b.is_read,
      rec_source: b.rec_source ?? null,
      rec_note: b.rec_note ?? null,
      source: b.source ?? 'personal',
    })),
  );
  try {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
  } catch {}
  return local.length;
}
