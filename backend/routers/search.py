from fastapi import APIRouter, Query
from backend.models import OMDBSearchResult
from backend.services import omdb_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[OMDBSearchResult])
async def search_movies(q: str = Query(..., min_length=1, description="Поисковый запрос")):
    """Поиск фильмов в OMDB по названию"""
    results = await omdb_service.search_movies(q)
    return results
