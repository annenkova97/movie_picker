import asyncio
import json
import os
from typing import Optional

from backend import database as db
from backend.services.llm import llm_service
from backend.services.omdb import omdb_service


CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "awards_catalog.json")


async def _ingest_one(imdb_id: str, award: str, award_year: Optional[int]) -> bool:
    """Возвращает True, если фильм добавлен; False — если уже был или не найден в OMDB."""
    existing = await db.get_award_by_imdb_id(imdb_id)
    if existing:
        return False

    movie_base = await omdb_service.get_movie_by_id(imdb_id)
    if not movie_base:
        print(f"[awards_seed] OMDB не вернул данные для {imdb_id}, пропускаю")
        return False

    await db.add_movie(
        movie_base,
        user_id=None,
        source="awards",
        in_library=False,
        award=award,
        award_year=award_year,
    )
    return True


async def sync_awards_catalog() -> None:
    """Идемпотентно подгружает фильмы из awards_catalog.json в БД.

    Для каждой записи: если фильма с этим IMDb ID ещё нет — добавляем
    с source='awards', in_library=False. Существующие записи не трогаем.
    """
    if not os.path.exists(CATALOG_PATH):
        print(f"[awards_seed] Файл каталога не найден: {CATALOG_PATH}")
        return

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)

    added = 0
    for entry in entries:
        imdb_id = entry.get("imdb_id")
        if not imdb_id:
            continue
        try:
            ok = await _ingest_one(
                imdb_id,
                entry.get("award", ""),
                entry.get("award_year"),
            )
            if ok:
                added += 1
                # маленькая пауза, чтобы не долбить OMDB
                await asyncio.sleep(0.2)
        except Exception as exc:
            print(f"[awards_seed] Ошибка при обработке {imdb_id}: {exc}")

    print(f"[awards_seed] Синк завершён: добавлено {added} из {len(entries)} записей")

    await backfill_plot_ru()


async def backfill_plot_ru() -> None:
    """Переводит plot на русский для всех фильмов, где plot_ru ещё пуст."""
    movies = await db.get_movies_missing_plot_ru()
    if not movies:
        return
    print(f"[awards_seed] Перевожу описания на русский: {len(movies)} фильмов")
    translated = 0
    for m in movies:
        try:
            ru = await llm_service.translate_plot(m.plot or "", m.title)
            if ru:
                await db.set_plot_ru(m.id, ru)
                translated += 1
            await asyncio.sleep(0.2)
        except Exception as exc:
            print(f"[awards_seed] Не удалось перевести {m.imdb_id}: {exc}")
    print(f"[awards_seed] Переведено {translated} из {len(movies)}")
