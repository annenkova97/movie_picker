from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from backend import database as db
from backend.models import InstagramImportRequest, Movie
from backend.models.movie import OMDBSearchResult
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
from backend.services.omdb import omdb_service

router = APIRouter(prefix="/api/instagram", tags=["instagram"])


@router.post("/import", response_model=list[Movie])
async def import_from_instagram(payload: InstagramImportRequest):
    """Импорт фильмов из Instagram Reel по ссылке."""
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

        added_movies: list[Movie] = []
        for item in movies_info:
            movie_base = movieinfo_to_moviebase(item)
            existing = await db.get_movie_by_imdb_id(movie_base.imdb_id)
            if existing:
                continue
            created = await db.add_movie(movie_base, source="instagram")
            added_movies.append(created)

        return added_movies

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
async def search_from_instagram(payload: InstagramImportRequest):
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
