from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend import database as db
from backend.models import Movie, MovieCreate, MovieUpdate, MovieBase
from backend.services import omdb_service, llm_service

router = APIRouter(prefix="/api/movies", tags=["movies"])


@router.get("", response_model=list[Movie])
async def get_movies(
    source: Optional[str] = Query(None, description="Фильтр по источнику: personal, top100, awards"),
    is_watched: Optional[bool] = Query(None, description="Фильтр по статусу просмотра")
):
    """Получить список всех фильмов"""
    return await db.get_all_movies(source=source, is_watched=is_watched)


@router.get("/{movie_id}", response_model=Movie)
async def get_movie(movie_id: int):
    """Получить фильм по ID"""
    movie = await db.get_movie_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    return movie


@router.post("", response_model=Movie)
async def add_movie(movie_data: MovieCreate):
    """
    Добавить фильм в список.
    Можно указать название или IMDb ID (tt1234567).
    """
    query = movie_data.query.strip()

    # Определяем, это IMDb ID или название
    if query.startswith("tt") and query[2:].isdigit():
        # Это IMDb ID
        movie_base = await omdb_service.get_movie_by_id(query)
    else:
        # Это название — ищем по названию
        movie_base = await omdb_service.get_movie_by_title(query)

    if not movie_base:
        raise HTTPException(
            status_code=404,
            detail=f"Фильм '{query}' не найден в OMDB"
        )

    # Проверяем, не добавлен ли уже этот фильм
    existing = await db.get_movie_by_imdb_id(movie_base.imdb_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Фильм '{movie_base.title}' уже есть в списке"
        )

    # Генерируем краткое описание через LLM
    if movie_base.plot:
        try:
            description = await llm_service.generate_short_description(
                movie_base.plot,
                movie_base.title
            )
            movie_base.description = description
        except Exception as e:
            # Если LLM не доступен, оставляем без описания
            print(f"Ошибка генерации описания: {e}")

    # Сохраняем в базу
    return await db.add_movie(movie_base, source="personal")


@router.post("/by-imdb/{imdb_id}", response_model=Movie)
async def add_movie_by_imdb_id(imdb_id: str, source: str = "personal"):
    """Добавить фильм по IMDb ID (используется для топ-100)"""
    # Проверяем, не добавлен ли уже
    existing = await db.get_movie_by_imdb_id(imdb_id)
    if existing:
        return existing

    movie_base = await omdb_service.get_movie_by_id(imdb_id)
    if not movie_base:
        raise HTTPException(status_code=404, detail=f"Фильм {imdb_id} не найден")

    # Генерируем описание
    if movie_base.plot:
        try:
            description = await llm_service.generate_short_description(
                movie_base.plot,
                movie_base.title
            )
            movie_base.description = description
        except Exception:
            pass

    return await db.add_movie(movie_base, source=source)


@router.patch("/{movie_id}", response_model=Movie)
async def update_movie(movie_id: int, update: MovieUpdate):
    """Обновить статус фильма (отметить просмотренным)"""
    movie = await db.get_movie_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")

    if update.is_watched is not None:
        return await db.update_movie(movie_id, update.is_watched)

    return movie


@router.delete("/{movie_id}")
async def delete_movie(movie_id: int):
    """Удалить фильм из списка"""
    success = await db.delete_movie(movie_id)
    if not success:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    return {"message": "Фильм удалён"}
