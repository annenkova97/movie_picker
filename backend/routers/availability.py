"""Доступность тайтла: где его можно посмотреть (watch-providers).

``GET /api/availability/{imdb_id}?region=RU`` — отдаёт нормализованную
доступность с кэшем (TTL 24ч внутри сервиса). Всегда 200 с консистентной
формой: на отсутствие данных возвращаем пустую доступность для региона,
чтобы фронт не городил спец-обработку null.
"""
from fastapi import APIRouter, Query, Request

from backend.models import WatchAvailability
from backend.rate_limit import limiter, user_or_ip_key
from backend.services.availability import get_availability

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.get("/{imdb_id}", response_model=WatchAvailability)
@limiter.limit("180/hour", key_func=user_or_ip_key)
async def availability(
    request: Request,
    imdb_id: str,
    region: str = Query("RU", min_length=2, max_length=2),
):
    region = region.upper()
    data = await get_availability(imdb_id, region)
    if data is None:
        return WatchAvailability(region=region)
    return data
