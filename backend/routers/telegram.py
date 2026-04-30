from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from backend import database as db
from backend.auth import get_current_user
from backend.models import Movie, MovieBase, TelegramImportRequest, User
from backend.services.instagram_reader import extract_movies
from backend.services.movie_resolver import resolve_movies
from backend.services.telegram_reader import (
    TelegramReaderError,
    fetch_post,
)


router = APIRouter(prefix="/api/telegram", tags=["telegram"])


async def _parse_post_to_moviebases(
    payload: TelegramImportRequest,
) -> tuple[list[MovieBase], list[str]]:
    """Fetch a t.me post and resolve mentioned movies to MovieBase records.

    Returns ``(resolved, unmatched_titles)``. Doesn't write to DB. Used by
    both ``/parse`` (guest) and ``/import`` (authenticated).
    """
    try:
        post = await run_in_threadpool(fetch_post, payload.url)
    except TelegramReaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    movies_info = await run_in_threadpool(
        extract_movies,
        "",          # no transcript — text posts only
        post.text,   # full post text goes in as "caption"
        None,
        False,
    )

    if not movies_info:
        raise HTTPException(
            status_code=422,
            detail="В этом посте не нашлось упоминаний фильмов",
        )

    return await resolve_movies(movies_info, log_tag="telegram/parse")


@router.post("/parse", response_model=list[MovieBase])
async def parse_telegram(payload: TelegramImportRequest):
    """Public — parse a t.me post and return matched movies.

    Mirrors ``/api/instagram/parse``: no DB write, used by guest mode where the
    client persists results in localStorage.
    """
    try:
        resolved, unmatched = await _parse_post_to_moviebases(payload)
        if not resolved:
            raise HTTPException(
                status_code=422,
                detail=f"Нашли упоминания, но не сопоставили с IMDb: {', '.join(unmatched)}",
            )
        return resolved
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/import", response_model=list[Movie])
async def import_from_telegram(
    payload: TelegramImportRequest,
    current_user: User = Depends(get_current_user),
):
    """Authenticated — parse + persist into the user's library."""
    try:
        resolved, unmatched = await _parse_post_to_moviebases(payload)

        added_movies: list[Movie] = []
        already_in_library: list[str] = []

        for movie_base in resolved:
            existing = await db.get_user_movie_by_imdb_id(
                movie_base.imdb_id, current_user.id,
            )
            if existing:
                already_in_library.append(existing.title)
                continue
            created = await db.add_movie(
                movie_base, user_id=current_user.id, source="telegram",
            )
            added_movies.append(created)

        if not added_movies:
            if already_in_library:
                raise HTTPException(
                    status_code=409,
                    detail=f"Уже на полке: {', '.join(already_in_library)}",
                )
            raise HTTPException(
                status_code=422,
                detail=f"Нашли упоминания, но не сопоставили с IMDb: {', '.join(unmatched)}",
            )

        return added_movies
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
