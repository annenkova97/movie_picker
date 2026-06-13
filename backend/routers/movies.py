from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from backend import database as db
from backend.auth import get_current_user
from backend.models import (
    BulkImportRequest,
    Movie,
    MovieCreate,
    MovieUpdate,
    User,
)
from backend.services import llm_service
from backend.services.title_search import find_movie_by_query, get_movie_by_key

router = APIRouter(prefix="/api/movies", tags=["movies"])


@router.get("", response_model=list[Movie])
async def get_movies(
    source: Optional[str] = Query(None, description="Фильтр по источнику: personal, top100, awards"),
    is_watched: Optional[bool] = Query(None, description="Фильтр по статусу просмотра"),
    in_library: Optional[bool] = Query(None, description="Только фильмы, сохранённые в библиотеке пользователя"),
    current_user: User = Depends(get_current_user),
):
    """Фильмы текущего пользователя."""
    return await db.get_all_movies(
        user_id=current_user.id,
        source=source,
        is_watched=is_watched,
        in_library=in_library,
    )


@router.get("/{movie_id}", response_model=Movie)
async def get_movie(movie_id: int, current_user: User = Depends(get_current_user)):
    """Получить фильм пользователя по ID."""
    movie = await db.get_user_movie_by_id(movie_id, current_user.id)
    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    return movie


@router.post("", response_model=Movie)
async def add_movie(
    movie_data: MovieCreate,
    current_user: User = Depends(get_current_user),
):
    """Добавить фильм в личную библиотеку по названию или IMDb ID (tt1234567)."""
    query = movie_data.query.strip()

    # Единый резолвер (tt-id / точный OMDB-match / кириллица через TMDb, включая
    # TMDb-only тайтлы без IMDb id). Раньше тут был отдельный OMDB-only путь,
    # который не находил русские/старые фильмы и сериалы.
    movie_base = await find_movie_by_query(query)

    if not movie_base:
        raise HTTPException(
            status_code=404,
            detail=f"Ничего похожего на «{query}» не нашли. Попробуй уточнить название."
        )

    existing = await db.get_user_movie_by_imdb_id(movie_base.imdb_id, current_user.id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Фильм '{movie_base.title}' уже есть у вас в списке"
        )

    if movie_base.plot:
        try:
            description = await llm_service.generate_short_description(
                movie_base.plot,
                movie_base.title
            )
            movie_base.description = description
        except Exception as e:
            print(f"Ошибка генерации описания: {e}")

    return await db.add_movie(
        movie_base,
        user_id=current_user.id,
        source="personal",
        rec_source=movie_data.rec_source,
        rec_note=movie_data.rec_note,
    )


@router.post("/by-imdb/{imdb_id}", response_model=Movie)
async def add_movie_by_imdb_id(
    imdb_id: str,
    source: str = "personal",
    current_user: User = Depends(get_current_user),
):
    """Добавить фильм в библиотеку пользователя по IMDb ID."""
    existing = await db.get_user_movie_by_imdb_id(imdb_id, current_user.id)
    if existing:
        return existing

    movie_base = await get_movie_by_key(imdb_id)
    if not movie_base:
        raise HTTPException(status_code=404, detail=f"Фильм {imdb_id} не найден")

    if movie_base.plot:
        try:
            description = await llm_service.generate_short_description(
                movie_base.plot,
                movie_base.title
            )
            movie_base.description = description
        except Exception:
            pass

    return await db.add_movie(movie_base, user_id=current_user.id, source=source)


@router.patch("/{movie_id}", response_model=Movie)
async def update_movie(
    movie_id: int,
    update: MovieUpdate,
    current_user: User = Depends(get_current_user),
):
    """Обновить поля фильма пользователя."""
    movie = await db.get_user_movie_by_id(movie_id, current_user.id)
    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")

    if (
        update.is_watched is None
        and update.rec_source is None
        and update.rec_note is None
        and update.user_rating is None
        and update.user_note is None
    ):
        return movie

    return await db.update_movie(
        movie_id,
        user_id=current_user.id,
        is_watched=update.is_watched,
        rec_source=update.rec_source,
        rec_note=update.rec_note,
        user_rating=update.user_rating,
        user_note=update.user_note,
    )


@router.post("/{movie_id}/save", response_model=Movie)
async def save_to_library(
    movie_id: int,
    is_watched: bool = False,
    current_user: User = Depends(get_current_user),
):
    """Сохранить фильм из каталога (awards) в личную библиотеку пользователя.

    Копирует запись каталога: каталог остаётся общим, у пользователя появляется
    своя запись.
    """
    catalog = await db.get_award_catalog_entry(movie_id)
    if not catalog:
        # возможно movie_id — это уже личная запись пользователя; тогда просто её проапдейтим
        own = await db.get_user_movie_by_id(movie_id, current_user.id)
        if own:
            return await db.update_movie(
                movie_id,
                user_id=current_user.id,
                is_watched=is_watched,
                in_library=True,
            )
        raise HTTPException(status_code=404, detail="Фильм не найден")

    existing = await db.get_user_movie_by_imdb_id(catalog.imdb_id, current_user.id)
    if existing:
        return await db.update_movie(
            existing.id,
            user_id=current_user.id,
            is_watched=is_watched,
            in_library=True,
        )

    # копия каталога в личную библиотеку
    from backend.models import MovieBase
    movie_base = MovieBase(
        imdb_id=catalog.imdb_id,
        title=catalog.title,
        original_title=catalog.original_title,
        year=catalog.year,
        genres=catalog.genres,
        description=catalog.description,
        plot=catalog.plot,
        plot_ru=catalog.plot_ru,
        cast=catalog.cast,
        director=catalog.director,
        poster_url=catalog.poster_url,
        imdb_rating=catalog.imdb_rating,
        awards=catalog.awards,
    )
    new_row = await db.add_movie(
        movie_base,
        user_id=current_user.id,
        source="awards",
        in_library=True,
        award=catalog.award,
        award_year=catalog.award_year,
    )
    if is_watched:
        new_row = await db.update_movie(new_row.id, user_id=current_user.id, is_watched=True)
    return new_row


@router.delete("/{movie_id}")
async def delete_movie(
    movie_id: int,
    current_user: User = Depends(get_current_user),
):
    """Удалить фильм из библиотеки пользователя."""
    success = await db.delete_movie(movie_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    return {"message": "Фильм удалён"}


@router.post("/bulk-import", response_model=list[Movie])
async def bulk_import(
    payload: BulkImportRequest,
    current_user: User = Depends(get_current_user),
):
    """Импорт массива фильмов в библиотеку пользователя.

    Используется при миграции гостевой (localStorage) библиотеки в аккаунт сразу
    после регистрации/логина. Идемпотентен по ``(user_id, imdb_id)``: если фильм
    уже на полке у этого пользователя — обновляем ``is_watched`` и оставляем
    запись (локальное состояние гостя считается более свежим). Если OMDB не
    знает фильм — пропускаем без ошибки, чтобы один битый imdb_id не уронил
    весь импорт.
    """
    imported: list[Movie] = []
    for item in payload.items:
        existing = await db.get_user_movie_by_imdb_id(item.imdb_id, current_user.id)
        if existing:
            updated = await db.update_movie(
                existing.id,
                user_id=current_user.id,
                is_watched=item.is_watched,
                in_library=True,
            )
            imported.append(updated or existing)
            continue

        movie_base = await get_movie_by_key(item.imdb_id)
        if not movie_base:
            print(f"[bulk-import] no record for {item.imdb_id}, skipping")
            continue

        if movie_base.plot:
            try:
                movie_base.description = await llm_service.generate_short_description(
                    movie_base.plot, movie_base.title,
                )
            except Exception as exc:
                print(f"[bulk-import] LLM description failed for {item.imdb_id}: {exc}")

        new_row = await db.add_movie(
            movie_base,
            user_id=current_user.id,
            source=item.source or "personal",
            rec_source=item.rec_source,
            rec_note=item.rec_note,
        )
        if item.is_watched:
            new_row = await db.update_movie(
                new_row.id, user_id=current_user.id, is_watched=True,
            )
        imported.append(new_row)
    return imported
