from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from backend import database as db
from backend.auth import get_current_user
from backend.models import InstagramImportRequest, Movie, User
from backend.models.movie import OMDBSearchResult
from backend.rate_limit import limiter, user_or_ip_key
from backend.services.instagram_reader import (
    InstagramReaderError,
    validate_url,
    download_reel,
    extract_audio,
    extract_frames,
    transcribe,
    extract_movies,
    movieinfo_to_moviebase,
    cleanup_temp_files,
)
from backend.services.llm import llm_service
from backend.services.omdb import omdb_service

router = APIRouter(prefix="/api/instagram", tags=["instagram"])


@router.post("/import", response_model=list[Movie])
@limiter.limit("10/hour", key_func=user_or_ip_key)
async def import_from_instagram(
    request: Request,
    payload: InstagramImportRequest,
    current_user: User = Depends(get_current_user),
):
    """Импорт фильмов из Instagram Reel по ссылке.

    Извлекает названия из транскрипта/подписи, ищет каждый в OMDB
    и сохраняет полную запись (с постером, годом, рейтингом) в библиотеку
    текущего пользователя. Дубликаты, уже лежащие на полке этого юзера,
    пропускаются.
    """
    try:
        url = validate_url(payload.url)

        video_path, caption = await run_in_threadpool(download_reel, url)
        audio_path = await run_in_threadpool(extract_audio, video_path)

        frame_paths: list[str] = []
        if payload.vision:
            frame_paths = await run_in_threadpool(extract_frames, video_path, 3)

        transcript = await run_in_threadpool(transcribe, audio_path)

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

        added_movies: list[Movie] = []
        already_in_library: list[str] = []
        unmatched: list[str] = []
        seen_ids: set[str] = set()

        for item in movies_info:
            display_title = item.title_ru or item.title_en or "?"
            candidates = await _search_omdb_with_fallbacks(
                item.title_en or "", item.title_ru or "", seen_ids, max_per_title=1,
            )
            if not candidates:
                unmatched.append(display_title)
                continue

            imdb_id = candidates[0].imdb_id
            existing = await db.get_user_movie_by_imdb_id(imdb_id, current_user.id)
            if existing:
                already_in_library.append(existing.title)
                continue

            movie_base = await omdb_service.get_movie_by_id(imdb_id)
            if not movie_base:
                unmatched.append(display_title)
                continue

            if movie_base.plot:
                try:
                    movie_base.description = await llm_service.generate_short_description(
                        movie_base.plot, movie_base.title,
                    )
                except Exception as exc:
                    print(f"[instagram/import] LLM description failed: {exc}")

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
    finally:
        cleanup_targets = []
        try:
            if 'audio_path' in locals() and audio_path:
                cleanup_targets.append(audio_path)
            if 'frame_paths' in locals() and frame_paths:
                cleanup_targets.extend(frame_paths)
        finally:
            cleanup_temp_files(cleanup_targets)


async def _search_omdb_with_fallbacks(
    title_en: str,
    title_ru: str,
    seen_ids: set[str],
    max_per_title: int = 3,
) -> list[OMDBSearchResult]:
    """Search OMDB trying multiple strategies until something is found."""
    results: list[OMDBSearchResult] = []

    def _collect(found: list[OMDBSearchResult]) -> bool:
        for r in found:
            if not r.poster_url or r.imdb_id in seen_ids:
                continue
            seen_ids.add(r.imdb_id)
            results.append(r)
            if len(results) >= max_per_title:
                return True
        return bool(results)

    # 1) Search by title_en (movie), then title_ru (movie)
    for query in [title_en, title_ru]:
        if not query:
            continue
        print(f"[instagram/search]   trying search(movie): '{query}'")
        if _collect(await omdb_service.search_movies(query)):
            return results

    # 2) Search without type restriction (finds series too)
    for query in [title_en, title_ru]:
        if not query:
            continue
        print(f"[instagram/search]   trying search(any type): '{query}'")
        if _collect(await omdb_service.search_movies(query, media_type="")):
            return results

    # 3) Exact title match via ?t=
    for query in [title_en, title_ru]:
        if not query:
            continue
        print(f"[instagram/search]   trying exact match: '{query}'")
        movie = await omdb_service.get_movie_by_title(query)
        if movie and movie.imdb_id not in seen_ids and movie.poster_url:
            seen_ids.add(movie.imdb_id)
            results.append(OMDBSearchResult(
                imdb_id=movie.imdb_id,
                title=movie.title,
                year=str(movie.year) if movie.year else "",
                poster_url=movie.poster_url,
            ))
            return results

    print(f"[instagram/search]   WARNING: nothing found for en='{title_en}' ru='{title_ru}'")
    return results


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

        video_path, caption = await run_in_threadpool(download_reel, url)
        print(f"[instagram/search] step: download OK")

        audio_path = await run_in_threadpool(extract_audio, video_path)
        print(f"[instagram/search] step: extract_audio OK")

        frame_paths: list[str] = []
        if payload.vision:
            frame_paths = await run_in_threadpool(extract_frames, video_path, 3)
            print(f"[instagram/search] step: extract_frames OK")

        transcript = await run_in_threadpool(transcribe, audio_path)
        print(f"[instagram/search] step: transcribe OK")
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
            found = await _search_omdb_with_fallbacks(
                title_en, title_ru, seen_ids,
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
        cleanup_targets = []
        try:
            if 'audio_path' in locals() and audio_path:
                cleanup_targets.append(audio_path)
            if 'frame_paths' in locals() and frame_paths:
                cleanup_targets.extend(frame_paths)
        finally:
            cleanup_temp_files(cleanup_targets)
