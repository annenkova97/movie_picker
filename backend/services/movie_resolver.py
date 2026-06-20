"""Shared OMDB-resolution logic used by Instagram and Telegram parsers.

Takes the LLM-extracted ``MovieInfo`` records and turns them into ``MovieBase``
records with full OMDB metadata. Decoupled from the source so any new
"extract movies from text" pipeline (Telegram, future Twitter, friend-shared
text) can reuse the same matching strategy.
"""

from __future__ import annotations

from backend.models.movie import MovieBase, OMDBSearchResult
from backend.services.instagram_reader import MovieInfo
from backend.services.llm import llm_service
from backend.services.omdb import omdb_service
from backend.services.title_search import get_movie_by_key
from backend.services.tmdb import tmdb_service


async def search_with_fallbacks(
    title_en: str,
    title_ru: str,
    seen_ids: set[str],
    max_per_title: int = 3,
    require_poster: bool = True,
    log_tag: str = "search",
) -> list[OMDBSearchResult]:
    """Resolve a title to IMDb candidates trying multiple sources in order.

    Stages: OMDB typed-movie → TMDb (movies + series, ru-RU) → OMDB any-type →
    OMDB exact-title. The TMDb stage is what makes **series** (and Russian-only
    or brand-new titles) resolvable: OMDB never finds a series by its Russian
    name, while TMDb matches it and yields an IMDb id we can hang the rest of
    the pipeline on. Tries the known-movie OMDB path first so well-known films
    keep their accurate, cheap match.

    De-dupes by imdb_id across the same caller via the ``seen_ids`` set. With
    ``require_poster`` (default) skips poster-less hits as a "real match"
    heuristic; callers that prefer recall over precision (the bot, which falls
    back to a text card) pass ``require_poster=False``.
    """
    results: list[OMDBSearchResult] = []

    def _collect(found: list[OMDBSearchResult]) -> bool:
        for r in found:
            if (require_poster and not r.poster_url) or r.imdb_id in seen_ids:
                continue
            seen_ids.add(r.imdb_id)
            results.append(r)
            if len(results) >= max_per_title:
                return True
        return bool(results)

    # 1. OMDB typed-movie — самый точный и дешёвый путь для известных фильмов.
    for query in [title_en, title_ru]:
        if not query:
            continue
        print(f"[{log_tag}]   trying OMDB search(movie): '{query}'")
        if _collect(await omdb_service.search_movies(query)):
            return results

    # 2. TMDb (фильмы + сериалы, ru-RU). Русский запрос первым — TMDb ищет на
    #    ru-RU, а сериалы в Reel'ах обычно названы по-русски. Тихо no-op без ключа.
    for query in [title_ru, title_en]:
        if not query:
            continue
        print(f"[{log_tag}]   trying TMDb search(any): '{query}'")
        if _collect(await tmdb_service.search_any(query)):
            return results

    # 3. OMDB any-type — добираем сериалы/прочее по англоязычному названию.
    for query in [title_en, title_ru]:
        if not query:
            continue
        print(f"[{log_tag}]   trying OMDB search(any type): '{query}'")
        if _collect(await omdb_service.search_movies(query, media_type="")):
            return results

    # 4. OMDB exact-title.
    for query in [title_en, title_ru]:
        if not query:
            continue
        print(f"[{log_tag}]   trying OMDB exact match: '{query}'")
        movie = await omdb_service.get_movie_by_title(query)
        if (
            movie
            and movie.imdb_id not in seen_ids
            and (movie.poster_url or not require_poster)
        ):
            seen_ids.add(movie.imdb_id)
            results.append(OMDBSearchResult(
                imdb_id=movie.imdb_id,
                title=movie.title,
                year=str(movie.year) if movie.year else "",
                poster_url=movie.poster_url,
            ))
            return results

    print(f"[{log_tag}]   WARNING: nothing found for en='{title_en}' ru='{title_ru}'")
    return results


async def resolve_movies(
    movies_info: list[MovieInfo],
    *,
    log_tag: str = "resolver",
) -> tuple[list[MovieBase], list[str]]:
    """Resolve LLM-extracted titles to MovieBase records.

    Returns ``(resolved, unmatched_titles)``. ``unmatched_titles`` keeps the
    Russian-or-English label of every movie we couldn't pin to an IMDb id, so
    the caller can show the user what slipped through.
    """
    resolved: list[MovieBase] = []
    unmatched: list[str] = []
    seen_ids: set[str] = set()

    for item in movies_info:
        display_title = item.title_ru or item.title_en or "?"

        candidates = await search_with_fallbacks(
            item.title_en or "",
            item.title_ru or "",
            seen_ids,
            max_per_title=1,
            log_tag=log_tag,
        )
        if not candidates:
            unmatched.append(display_title)
            continue

        # Кандидат может быть TMDb-only (ключ ``tmdb:…``) — диспетчеризуем
        # вместо прямого OMDB, иначе старый/русский фильм без IMDb id потеряем.
        movie_base = await get_movie_by_key(candidates[0].imdb_id)
        if not movie_base:
            unmatched.append(display_title)
            continue

        if movie_base.plot:
            try:
                movie_base.description = await llm_service.generate_short_description(
                    movie_base.plot, movie_base.title,
                )
            except Exception as exc:
                print(f"[{log_tag}] LLM description failed: {exc}")

        resolved.append(movie_base)

    return resolved, unmatched
