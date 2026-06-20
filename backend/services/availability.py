"""Доступность тайтлов (watch-providers) с кэшем — единая точка cache-or-fetch.

Используется и роутером ``/api/availability``, и подмешиванием доступности в
``/api/recommend``. Доступность per-тайтл+регион, поэтому кэш общий для всех
пользователей (DRY: один запрос в TMDb покрывает всех, у кого этот фильм).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from backend import database as db
from backend.services.tmdb import tmdb_service


# Провайдеры меняются редко; сутки — разумный компромисс между свежестью и
# числом обращений к TMDb. Протухший кэш перезапрашиваем, при сбое — отдаём
# протухшее (лучше слегка устаревшие бейджи, чем пустой экран).
CACHE_TTL = timedelta(hours=24)


async def get_availability(imdb_id: str, region: str) -> Optional[dict]:
    """Доступность тайтла в регионе: свежий кэш → fetch → upsert.

    None только если данных нет совсем (TMDb выключен / ключ нерезолвим /
    сетевая ошибка и пустой кэш). Иначе — нормализованный dict (см. tmdb)."""
    region = (region or "RU").upper()
    cached = await db.get_watch_providers_cache(imdb_id, region)
    if cached:
        payload, fetched_at = cached
        if datetime.utcnow() - fetched_at < CACHE_TTL:
            return payload

    fresh = await tmdb_service.get_watch_providers(imdb_id, region)
    if fresh is None:
        # Запрос не удался — отдаём протухший кэш, если он есть.
        return cached[0] if cached else None

    try:
        await db.upsert_watch_providers_cache(imdb_id, region, fresh)
    except Exception as exc:  # кэш — best-effort, не роняем ответ
        print(f"[availability] cache upsert failed for {imdb_id}/{region}: {exc}")
    return fresh


def is_available_on(availability: Optional[dict], services: list[int]) -> bool:
    """Есть ли тайтл по подписке (``flatrate``) на одном из сервисов юзера.

    Учитываем только ``flatrate`` (подписка) — для «что посмотреть сегодня»
    аренда/покупка это другой момент решения. Пустой ``services`` → False
    (нечего сопоставлять; фильтрацией это разруливает вызывающий)."""
    if not availability or not services:
        return False
    service_set = set(services)
    return any(
        p.get("provider_id") in service_set
        for p in (availability.get("flatrate") or [])
    )
