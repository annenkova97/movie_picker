#!/usr/bin/env python3
"""One-off: move Telegram-bot-saved movies from the local SQLite DB into the
shared Railway Postgres, so the bot and the web app converge on one profile.

Why a script and not a direct copy: the two stores have different schemas and
the user is keyed by ``telegram_id``, so we go through the normal db layer to
re-create rows correctly and idempotently (skip anything already present).

Two modes, auto-selected by whether DATABASE_URL is set (see backend.config):

  EXPORT  (no DATABASE_URL → SQLite)
      python scripts/migrate_local_telegram_to_postgres.py
      Reads every user that has a telegram_id + their in-library movies from
      the local SQLite file and writes them to MIGRATION_FILE. Read-only.

  IMPORT  (DATABASE_URL set → Postgres)
      python scripts/migrate_local_telegram_to_postgres.py            # dry-run
      python scripts/migrate_local_telegram_to_postgres.py --commit   # writes
      Reads MIGRATION_FILE and upserts the users (by telegram_id) and their
      movies into Postgres. Dry-run by default; --commit actually writes.
      Idempotent: a movie already on the user's shelf (same imdb_id) is skipped.

Typical flow:
  1) run export locally (produces the JSON)
  2) put the Railway Postgres DATABASE_URL in .env
  3) run import --commit
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# Make `backend` importable when run as `python scripts/...`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import config
from backend import database as db
from backend.models.movie import MovieBase

MIGRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "telegram_migration_export.json",
)

# Fields add_movie() reproduces from a MovieBase.
_BASE_FIELDS = (
    "imdb_id", "title", "original_title", "year", "genres", "description",
    "plot", "plot_ru", "cast", "director", "poster_url", "imdb_rating", "awards",
)


async def export_from_sqlite() -> None:
    await db.init_db()
    users = await db.get_all_telegram_users() if hasattr(db, "get_all_telegram_users") else None
    if users is None:
        # No dedicated helper — read the users table directly via the movies API.
        # We only need telegram users; fetch them straight from SQLite.
        import aiosqlite

        async with aiosqlite.connect(config.DATABASE_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            rows = await (await conn.execute(
                "SELECT id, telegram_id, email, name, avatar_url "
                "FROM users WHERE telegram_id IS NOT NULL"
            )).fetchall()
            users = [dict(r) for r in rows]

    payload = {"users": []}
    for u in users:
        movies = await db.get_all_movies(user_id=u["id"], in_library=True)
        payload["users"].append({
            "telegram_id": u["telegram_id"],
            "email": u["email"],
            "name": u.get("name"),
            "avatar_url": u.get("avatar_url"),
            "movies": [m.model_dump() for m in movies],
        })

    with open(MIGRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    total = sum(len(u["movies"]) for u in payload["users"])
    print(f"EXPORT done → {MIGRATION_FILE}")
    print(f"  {len(payload['users'])} telegram user(s), {total} in-library movie(s):")
    for u in payload["users"]:
        print(f"  • tg:{u['telegram_id']} ({u['email']}) — {len(u['movies'])} movies")
        for m in u["movies"]:
            print(f"      - {m['title']} ({m.get('year')})  [{m['imdb_id']}]")


async def import_into_postgres(commit: bool) -> None:
    if not os.path.exists(MIGRATION_FILE):
        sys.exit(f"ERROR: {MIGRATION_FILE} not found. Run the export step first.")

    with open(MIGRATION_FILE, encoding="utf-8") as f:
        payload = json.load(f)

    await db.init_db()
    mode = "COMMIT" if commit else "DRY-RUN"
    print(f"IMPORT ({mode}) into Postgres\n")

    added = skipped = 0
    for u in payload["users"]:
        tg_id = int(u["telegram_id"])
        user_row = await db.get_user_by_telegram_id(tg_id)
        if user_row:
            print(f"user tg:{tg_id} → exists in Postgres (id={user_row['id']})")
        else:
            print(f"user tg:{tg_id} → NOT in Postgres; will create ({u['email']})")
            if commit:
                user_row = await db.create_user(
                    email=u["email"], telegram_id=tg_id,
                    name=u.get("name"), avatar_url=u.get("avatar_url"),
                )
        user_id = user_row["id"] if user_row else None

        for m in u["movies"]:
            existing = None
            if user_id is not None:
                existing = await db.get_user_movie_by_imdb_id(m["imdb_id"], user_id)
            if existing:
                print(f"   skip (already on shelf): {m['title']}")
                skipped += 1
                continue

            print(f"   add: {m['title']} ({m.get('year')})")
            added += 1
            if commit and user_id is not None:
                base = MovieBase(**{k: m.get(k) for k in _BASE_FIELDS if m.get(k) is not None})
                created = await db.add_movie(
                    base, user_id=user_id,
                    source=m.get("source") or "telegram", in_library=True,
                )
                if m.get("is_watched"):
                    await db.update_movie(created.id, user_id=user_id, is_watched=True)

    print(f"\n{mode}: {added} to add, {skipped} already present.")
    if not commit and added:
        print("Re-run with --commit to actually write.")


def main() -> None:
    commit = "--commit" in sys.argv
    if config.USE_POSTGRES:
        asyncio.run(import_into_postgres(commit))
    else:
        print("DATABASE_URL not set → EXPORT mode (reading local SQLite).\n")
        asyncio.run(export_from_sqlite())


if __name__ == "__main__":
    main()
