"""Resolve LLM-extracted book mentions to BookBase records.

The books analogue of ``services/movie_resolver.resolve_movies``. Takes
``BookInfo`` records and looks each up via the ``book_search`` dispatcher
(Google Books → Open Library), preferring an "author + title" query when the
author is known (that's what makes «Бродский» resolve).
"""

from __future__ import annotations

from backend.models.book import BookBase
from backend.services import book_search
from backend.services.media_extractor import BookInfo


def _query_for(item: BookInfo) -> str:
    title = item.title_ru or item.title_en
    return f"{title} {item.author}".strip() if item.author else title


async def resolve_books(
    books_info: list[BookInfo],
    *,
    log_tag: str = "resolver",
) -> tuple[list[BookBase], list[str]]:
    """Return ``(resolved, unmatched_titles)``."""
    resolved: list[BookBase] = []
    unmatched: list[str] = []
    seen: set[str] = set()

    for item in books_info:
        display = item.title_ru or item.title_en or "?"
        query = _query_for(item)
        if not query:
            continue

        results = await book_search.search_books(query)
        if not results:
            unmatched.append(display)
            continue

        work_key = results[0].work_key
        if work_key in seen:
            continue
        seen.add(work_key)

        base = await book_search.get_book_by_key(work_key)
        if base:
            resolved.append(base)
        else:
            unmatched.append(display)

    return resolved, unmatched
