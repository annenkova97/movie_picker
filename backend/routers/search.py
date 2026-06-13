from fastapi import APIRouter, Query, HTTPException, Request
from backend.models import OMDBSearchResult, MoviePreview
from backend.rate_limit import limiter
from backend.services.title_search import get_movie_by_key, search_title

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[OMDBSearchResult])
@limiter.limit("60/minute")
async def search_movies(
    request: Request,
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
):
    """Поиск фильмов по названию через единый пайплайн (TMDB → OMDB → перевод).

    Раньше веб-поиск ходил только в OMDB+перевод и потому плохо находил русские
    (особенно старые) фильмы и сериалы. Теперь идёт через ``search_title``, как
    и бот: для кириллицы первым работает TMDb, отдавая русские названия и, при
    необходимости, синтетические ``tmdb:`` ключи. Публичный, без user_id.
    """
    return await search_title(q)


@router.get("/preview/{imdb_id:path}", response_model=MoviePreview)
@limiter.limit("60/minute")
async def get_movie_preview(
    request: Request,
    imdb_id: str,
):
    """Детальный превью фильма по внешнему ключу (``tt…`` или ``tmdb:…``)."""
    movie = await get_movie_by_key(imdb_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    return MoviePreview(
        imdb_id=movie.imdb_id,
        title=movie.title,
        year=movie.year,
        media_type=movie.media_type,
        poster_url=movie.poster_url,
        imdb_rating=movie.imdb_rating,
        genres=movie.genres,
        plot=movie.plot,
        director=movie.director,
        cast=movie.cast,
        awards=movie.awards,
    )
