#!/usr/bin/env python3
"""One-off: проставить ``media_type`` (movie/series) у УЖЕ сохранённых фильмов.

Контекст: распознавание сериалов добавили позже, чем накопилась библиотека.
У старых записей ``media_type`` лежит дефолтное ``'movie'`` — и сериалы висят
во вкладке «Фильмы». Этот скрипт перепроходит по сохранённым ``imdb_id``,
спрашивает у OMDB настоящий ``Type`` и обновляет колонку там, где это сериал.

Хранилище выбирается автоматически по ``DATABASE_URL`` (как и в остальном
приложении): задан → Postgres (Railway), не задан → локальный SQLite.
Нужен ``OMDB_API_KEY`` в окружении — иначе OMDB ничего не вернёт.

Запуск (dry-run по умолчанию — только показывает, что изменится):

    DATABASE_URL='postgresql://...' OMDB_API_KEY='...' \
        python scripts/backfill_media_type.py

    # реально записать:
    DATABASE_URL='postgresql://...' OMDB_API_KEY='...' \
        python scripts/backfill_media_type.py --commit

Идемпотентен: дешёвый дедуп по ``imdb_id`` (один запрос к OMDB на тайтл,
плюс встроенный суточный кэш сервиса), повторный прогон ничего не ломает.
"""
from __future__ import annotations

import asyncio
import os
import sys

# Make `backend` importable when run as `python scripts/...`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import USE_POSTGRES
from backend.services.omdb import omdb_service


async def _distinct_imdb_ids() -> list[str]:
    """Все уникальные imdb_id из таблицы movies (оба хранилища)."""
    if USE_POSTGRES:
        from backend import db_postgres
        await db_postgres.init_db()
        async with db_postgres._pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT imdb_id FROM movies")
        return [r[0] for r in rows if r[0]]

    import aiosqlite
    from backend.config import DATABASE_PATH
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        async with conn.execute("SELECT DISTINCT imdb_id FROM movies") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows if r[0]]


async def _update_media_type(imdb_id: str, media_type: str) -> int:
    """Проставляет media_type всем строкам с этим imdb_id. Возвращает кол-во
    реально изменённых строк (где значение отличалось)."""
    if USE_POSTGRES:
        from backend import db_postgres
        async with db_postgres._pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE movies SET media_type = $1 "
                "WHERE imdb_id = $2 AND media_type IS DISTINCT FROM $1",
                media_type, imdb_id,
            )
        # asyncpg возвращает строку вида "UPDATE <n>".
        return int(res.split()[-1])

    import aiosqlite
    from backend.config import DATABASE_PATH
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        cur = await conn.execute(
            "UPDATE movies SET media_type = ? "
            "WHERE imdb_id = ? AND (media_type IS NULL OR media_type != ?)",
            (media_type, imdb_id, media_type),
        )
        await conn.commit()
        return cur.rowcount


async def main(commit: bool) -> None:
    store = "Postgres" if USE_POSTGRES else "SQLite"
    print(f"[backfill] хранилище: {store} | режим: "
          f"{'COMMIT' if commit else 'dry-run'}\n")

    imdb_ids = await _distinct_imdb_ids()
    print(f"[backfill] уникальных тайтлов в библиотеке: {len(imdb_ids)}\n")

    series: list[str] = []
    skipped: list[str] = []

    for imdb_id in imdb_ids:
        movie = await omdb_service.get_movie_by_id(imdb_id)
        if not movie:
            skipped.append(imdb_id)
            print(f"  ?  {imdb_id}: OMDB не знает — пропуск")
            continue
        if movie.media_type == "series":
            series.append(imdb_id)
            print(f"  →  {imdb_id}: «{movie.title}» — СЕРИАЛ")

    print(f"\n[backfill] сериалов найдено: {len(series)} "
          f"(пропущено по OMDB: {len(skipped)})")

    if not commit:
        print("[backfill] dry-run — ничего не записано. "
              "Перезапусти с --commit, чтобы применить.")
        return

    changed = 0
    for imdb_id in series:
        changed += await _update_media_type(imdb_id, "series")
    print(f"[backfill] обновлено строк: {changed}")


if __name__ == "__main__":
    asyncio.run(main(commit="--commit" in sys.argv))
