from fastapi import APIRouter, Depends, Query
import re
from backend.auth import get_current_user
from backend.models import OMDBSearchResult, User
from backend.services import omdb_service, llm_service

router = APIRouter(prefix="/api/search", tags=["search"])


def _has_cyrillic(text: str) -> bool:
    return bool(re.search('[а-яА-ЯёЁ]', text))


@router.get("", response_model=list[OMDBSearchResult])
async def search_movies(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    current_user: User = Depends(get_current_user),
):
    """Поиск фильмов в OMDB по названию. Автоматически переводит русские запросы."""
    search_q = q
    if _has_cyrillic(q):
        try:
            search_q = await llm_service.translate_movie_title(q)
            print(f"Поиск: перевод '{q}' → '{search_q}'")
        except Exception as e:
            print(f"Ошибка перевода при поиске, используем оригинал: {e}")
    results = await omdb_service.search_movies(search_q)
    return results
