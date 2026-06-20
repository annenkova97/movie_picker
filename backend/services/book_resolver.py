"""Resolve LLM-extracted book mentions to BookBase records.

The books analogue of ``services/movie_resolver.resolve_movies``. Takes
``BookInfo`` records and looks each up via the ``book_search`` dispatcher
(Google Books → Open Library), preferring an "author + title" query when the
author is known (that's what makes «Бродский» resolve).
"""

from __future__ import annotations

from typing import Optional

from backend.models.book import BookBase, BookSearchResult
from backend.services import book_search
from backend.services.media_extractor import BookInfo
from backend.services.text_match import normalize_title, title_score


def _query_for(item: BookInfo) -> tuple[str, str]:
    """Вернуть ``(search_query, clean_title)``.

    При известном авторе строим структурированный запрос
    ``intitle:"…" inauthor:"…"`` — Google Books так точнее находит конкретное
    произведение (именно это «спасает» Бродского), а ранжируем потом по чистому
    названию.
    """
    title = (item.title_ru or item.title_en or "").strip()
    author = (item.author or "").strip()
    if author:
        return f'intitle:"{title}" inauthor:"{author}"', title
    return title, title


def _author_overlap(a: str, b: Optional[str]) -> bool:
    if not a or not b:
        return False
    return bool(set(normalize_title(a).split()) & set(normalize_title(b).split()))


def _candidate_score(r: BookSearchResult, title: str, author: str) -> float:
    score = title_score(title, r.title)
    if _author_overlap(author, r.author):
        score += 0.3
    return score


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
        query, clean_title = _query_for(item)
        if not query:
            continue

        results = await book_search.search_books(query, rank_query=clean_title)
        if not results:
            unmatched.append(display)
            continue

        # Выбираем лучшее совпадение, а не «первый результат»: для старых книг
        # Google нередко ставит учебник/чужое издание выше нужного.
        author = (item.author or "").strip()
        best = max(results, key=lambda r: _candidate_score(r, clean_title, author))
        if best.work_key in seen:
            continue
        seen.add(best.work_key)

        base = await book_search.get_book_by_key(best.work_key)
        if base:
            resolved.append(base)
        else:
            unmatched.append(display)

    return resolved, unmatched
