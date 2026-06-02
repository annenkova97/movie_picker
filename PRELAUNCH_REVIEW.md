# Ленточка — Pre-launch review

Reviewed before rolling out to users. Grouped by priority. Items marked **✅ done**
were fixed in this iteration; the rest are recommended follow-ups.

## P0 — must do before launch

1. **Untrack the dev database.** `backend/data/movies.db` is committed to git.
   It will leak local/user data and cause binary merge conflicts. `.gitignore`
   now excludes it (✅), but the already-tracked copy must be removed once:
   ```
   git rm --cached backend/data/movies.db
   ```
2. **Secrets hygiene.** `.env.save` sat in the working tree un-ignored. Now
   gitignored (✅). Verify it was never pushed: `git log --all -- .env.save`.
   If it ever was, **rotate** `OMDB_API_KEY`, `ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `APIFY_TOKEN`, `JWT_SECRET`,
   `TMDB_API_KEY`.
3. **Production env vars.** Confirm on Railway:
   - `DATABASE_URL` is set → Postgres (SQLite is ephemeral and wipes on every
     redeploy). The active engine is logged at boot (`[db] Using …`).
   - `CORS_ALLOW_ORIGINS` = the production frontend/Mini-App domain.
   - `JWT_SECRET` is a real 32-byte secret (the app already refuses to start
     without one — good).

## P1 — strongly recommended

4. **CI** — added `.github/workflows/ci.yml` (✅) running `pytest` + `tsc` +
   `vitest` on every PR. The stale Instagram tests are fixed; the live-network
   case is gated behind `RUN_INTEGRATION=1`. Suite is green: **50 passed, 1 skipped**.
5. **Fake runtimes.** `frontend-new/src/types.ts` `parseRuntime()` is a stub
   that returns a constant `110`, so every "1 ч 50 мин" in the UI is invented.
   Either fetch real runtime from OMDB (`Runtime` field) or hide the field.
6. **Awards catalog is small (38 entries, Oscar/Globe/Cannes only).** This
   directly limits the quality of the new awards row, the "Все" browse, and the
   mood-pick mixing (#4/#5). Expand `backend/data/awards_catalog.json`
   (BAFTA, more years) before promoting these features.
7. **External-API resilience.** `omdb`, `openlibrary`, and per-add LLM calls
   have no caching or circuit-breaker. OMDB free tier is ~1k/day. `search.py`
   and `movies.py`/`books.py` will surface 5xx if a provider hiccups. Add a
   short-TTL cache on search/preview and graceful degradation.

## P2 — follow-ups

8. **Test coverage gaps**: no component tests for the new wine-deep screens
   (add smokes so the gear→settings / film→detail / "Все"→browse / Книги→shelf
   wiring can't silently regress to `console.log` again); no tests for the bot
   handlers or the DB layer directly.
9. **Light theme polish.** The wine-deep flow now supports a light theme
   (default stays dark). A few muted captions are slightly low-contrast in light
   mode — a quick token pass would finish it.
10. **`bulk_import` cost.** Guest→account migration (movies and now books) makes
    one external call per item with no concurrency cap. A large guest list will
    be slow and can hammer OMDB/Open Library. Consider bounded concurrency.
11. **Book "import by link"** is scoped to title / Open Library / Goodreads URL
    parsing in search. Deep social-link (Telegram/Instagram) book extraction is
    deferred — the readers are tuned for movie titles.

## What shipped this iteration

Fixes #1–#7 (settings sheet, visible RU/EN switch + device-language default,
"С возвращением" greeting, awards mixed into mood picks, real awards data,
working "Все" browse, movie-click detail, in-app search) and #8 (Books, full
parity: Open Library service, `books` table in both DB engines, CRUD + search +
preview + mood-recommend + guest→account migration, reading shelves, book
detail). Backend: 50 tests green. Frontend: 18 tests + clean type-check.
