from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from backend import database as db
from backend.auth import get_current_user
from backend.models import InstagramImportRequest, Movie, MovieBase, User
from backend.models.movie import OMDBSearchResult
from backend.rate_limit import limiter, user_or_ip_key
from backend.services.instagram_reader import (
    InstagramReaderError,
    validate_url,
    download_reel,
    extract_frames,
    extract_movies,
    cleanup_temp_files,
)
from backend.services.movie_resolver import (
    resolve_movies,
    search_omdb_with_fallbacks,
)


router = APIRouter(prefix="/api/instagram", tags=["instagram"])


async def _parse_reel_to_moviebases(
    payload: InstagramImportRequest,
) -> tuple[list[MovieBase], list[str]]:
    """Скачивает Reel, извлекает фильмы и резолвит их в MovieBase.

    Возвращает ``(resolved, unmatched_titles)``. Не сохраняет ничего в БД.
    Бросает ``HTTPException(422)`` если в Reel нет упоминаний фильмов.

    Эту функцию используют оба endpoint'а: ``/import`` (для авторизованного
    пользователя) и ``/parse`` (для гостя).
    """
    url = validate_url(payload.url)

    # Apify-actor отдаёт сразу caption + готовый transcript + видео в их KVS,
    # так что отдельный Whisper и аудио-экстракция здесь не нужны.
    video_path, caption, transcript = await run_in_threadpool(download_reel, url)

    frame_paths: list[str] = []
    # Кадры нужны только для vision-режима, и только если видео реально скачали.
    if payload.vision and video_path:
        frame_paths = await run_in_threadpool(extract_frames, video_path, 3)

    try:
        movies_info = await run_in_threadpool(
            extract_movies,
            transcript,
            caption,
            frame_paths if payload.vision else None,
            payload.vision,
        )

        if not movies_info:
            raise HTTPException(
                status_code=422,
                detail="В этом Reel не нашлось упоминаний фильмов",
            )

        return await resolve_movies(movies_info, log_tag="instagram/parse")
    finally:
        if frame_paths:
            cleanup_temp_files(frame_paths)


@router.post("/parse", response_model=list[MovieBase])
@limiter.limit("10/hour")
async def parse_instagram(request: Request, payload: InstagramImportRequest):
    """Распарсить Reel и вернуть фильмы без сохранения в БД.

    Публичный endpoint — используется гостями. Клиент сам кладёт результат
    в localStorage. Лимит по IP: пайплайн дорогой (Apify + transcript + GPT),
    а авторизации тут нет, так что это самый уязвимый к абьюзу путь.
    """
    try:
        resolved, unmatched = await _parse_reel_to_moviebases(payload)
        if not resolved:
            raise HTTPException(
                status_code=422,
                detail=f"Нашли упоминания, но не сопоставили с IMDb: {', '.join(unmatched)}",
            )
        return resolved
    except HTTPException:
        raise
    except InstagramReaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/import", response_model=list[Movie])
@limiter.limit("10/hour", key_func=user_or_ip_key)
async def import_from_instagram(
    request: Request,
    payload: InstagramImportRequest,
    current_user: User = Depends(get_current_user),
):
    """Импорт фильмов из Instagram Reel в библиотеку авторизованного пользователя.

    Дубликаты, уже лежащие на полке этого юзера, пропускаются.
    """
    try:
        resolved, unmatched = await _parse_reel_to_moviebases(payload)

        added_movies: list[Movie] = []
        already_in_library: list[str] = []

        for movie_base in resolved:
            existing = await db.get_user_movie_by_imdb_id(
                movie_base.imdb_id, current_user.id
            )
            if existing:
                already_in_library.append(existing.title)
                continue
            created = await db.add_movie(
                movie_base, user_id=current_user.id, source="instagram"
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
    except InstagramReaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/search", response_model=list[OMDBSearchResult])
@limiter.limit("10/hour", key_func=user_or_ip_key)
async def search_from_instagram(
    request: Request,
    payload: InstagramImportRequest,
    current_user: User = Depends(get_current_user),
):
    """Извлечь названия фильмов из Instagram Reel и найти их в OMDB."""
    try:
        url = validate_url(payload.url)
        print(f"[instagram/search] url: {url}")

        video_path, caption, transcript = await run_in_threadpool(download_reel, url)
        print(
            f"[instagram/search] step: apify OK "
            f"(video={'yes' if video_path else 'no'}, "
            f"transcript={'yes' if transcript else 'no'})"
        )

        frame_paths: list[str] = []

        if payload.vision and video_path:
            frame_paths = await run_in_threadpool(extract_frames, video_path, 3)
            print(f"[instagram/search] step: extract_frames OK")

        print(f"[instagram/search] transcript: {transcript[:200]}")
        print(f"[instagram/search] caption: {caption[:200] if caption else '(empty)'}")

        movies_info = await run_in_threadpool(
            extract_movies,
            transcript,
            caption,
            frame_paths if payload.vision else None,
            payload.vision,
        )
        print(f"[instagram/search] step: extract_movies OK → {len(movies_info)} movies")
        print(f"[instagram/search] extracted: {movies_info}")

        results: list[OMDBSearchResult] = []
        seen_ids: set[str] = set()
        for item in movies_info:
            title_en = item.title_en or ""
            title_ru = item.title_ru or ""
            print(f"[instagram/search] searching for: en='{title_en}' ru='{title_ru}'")
            found = await search_omdb_with_fallbacks(
                title_en, title_ru, seen_ids, log_tag="instagram/search",
            )
            print(f"[instagram/search]   → found {len(found)} results")
            results.extend(found)

        print(f"[instagram/search] step: OMDB search OK → {len(results)} total results")
        return results

    except InstagramReaderError as exc:
        print(f"[instagram/search] ERROR (reader): {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        print(f"[instagram/search] ERROR (unexpected): {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if 'frame_paths' in locals() and frame_paths:
            cleanup_temp_files(frame_paths)
