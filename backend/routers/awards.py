from fastapi import APIRouter, Query
from typing import Optional

from backend import database as db
from backend.models import Movie

router = APIRouter(prefix="/api/awards", tags=["awards"])


@router.get("", response_model=list[Movie])
async def get_awards_catalog(limit: Optional[int] = Query(None, ge=1, le=500)):
    """Каталог фильмов-лауреатов (Оскар, Золотой глобус, Каннская ветвь…).
    Отсортирован по году награды — свежие сверху."""
    return await db.get_awards(limit=limit)
