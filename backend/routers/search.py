from fastapi import APIRouter, Depends, Query, HTTPException, Request
import re
from backend.auth import get_current_user
from backend.models import OMDBSearchResult, MoviePreview, User
from backend.rate_limit import limiter, user_or_ip_key
from backend.services import omdb_service, llm_service

router = APIRouter(prefix="/api/search", tags=["search"])


def _has_cyrillic(text: str) -> bool:
    return bool(re.search('[а-яА-ЯёЁ]', text))


@router.get("", response_model=list[OMDBSearchResult])
@limiter.limit("60/minute", key_func=user_or_ip_key)
async def search_movies(
    request: Request,
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


@router.get("/preview/{imdb_id}", response_model=MoviePreview)
@limiter.limit("60/minute", key_func=user_or_ip_key)
async def get_movie_preview(
    request: Request,
    imdb_id: str,
    current_user: User = Depends(get_current_user),
):
    """Получить детальный превью фильма по IMDb ID — без сохранения в БД."""
    movie = await omdb_service.get_movie_by_id(imdb_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    return MoviePreview(
        imdb_id=movie.imdb_id,
        title=movie.title,
        year=movie.year,
        poster_url=movie.poster_url,
        imdb_rating=movie.imdb_rating,
        genres=movie.genres,
        plot=movie.plot,
        director=movie.director,
        cast=movie.cast,
        awards=movie.awards,
    )
