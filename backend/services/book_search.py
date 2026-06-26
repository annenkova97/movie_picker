"""Единая точка поиска книг: Google Books → Open Library (фолбэк).

Зеркало ``services/title_search.py`` для фильмов. Google Books идёт первым —
он сильно лучше находит русскоязычные книги (для кириллицы добавляем
``langRestrict=ru``). Если Google ничего не вернул или упал по квоте —
откатываемся на Open Library.

Выдачу локально ре-ранжируем по близости названия (``text_match``): Google
часто ставит учебники/дубли-издания/переводы выше нужной классики, особенно для
старых русских книг. Детали тянем по префиксу ключа: ``gb:…`` → Google Books,
``OL…W`` → Open Library.
"""

from __future__ import annotations

from typing import Optional

from backend.models.book import BookBase, BookSearchResult
from backend.services.googlebooks import googlebooks_service, is_google_key
from backend.services.openlibrary import openlibrary_service
from backend.services.text_match import title_score
from backend.services.title_search import has_cyrillic


def _has_operators(query: str) -> bool:
    return "intitle:" in query or "inauthor:" in query


async def _google(query: str, prefer_lang: Optional[str]) -> list[BookSearchResult]:
    """Google Books с подстраховкой по языку.

    ``langRestrict=ru`` поднимает русские издания над переводами, но Google
    далеко не всем русским томам проставляет язык — под фильтром они выпадают,
    и автор вроде «Бродский» может вернуть пусто. Поэтому при пустом ответе
    повторяем тот же запрос без ограничения языка, прежде чем сдаваться.
    """
    results = await googlebooks_service.search_books(query, prefer_lang=prefer_lang)
    if not results and prefer_lang:
        results = await googlebooks_service.search_books(query)
    return results


def _rerank(results: list[BookSearchResult], key: str) -> list[BookSearchResult]:
    """Стабильно отсортировать по близости названия к ``key`` (лучшее — выше)."""
    return [
        r for _, r in sorted(
            enumerate(results),
            key=lambda iv: (-title_score(key, iv[1].title), iv[0]),
        )
    ]


async def search_books(
    query: str, *, rank_query: Optional[str] = None,
) -> list[BookSearchResult]:
    """Карточки книг для UI. Google Books первым, Open Library — фолбэк.

    ``rank_query`` — по какой строке ранжировать (по умолчанию сам ``query``).
    Резолвер передаёт сюда чистое название, даже когда ``query`` собран из
    операторов ``intitle:/inauthor:`` для recall'а.
    """
    query = query.strip()
    if not query:
        return []

    rank_by = rank_query or query
    prefer_lang = "ru" if has_cyrillic(query) else None
    results = await _google(query, prefer_lang)

    # Старые/редкие книги: если обычный запрос пуст — пробуем строгий intitle
    # перед откатом на Open Library (он по-русски почти бесполезен).
    if not results and not _has_operators(query):
        results = await _google(f"intitle:{query}", prefer_lang)

    if not results:
        results = await openlibrary_service.search_books(query)

    return _rerank(results, rank_by)


async def get_book_by_key(work_key: str) -> Optional[BookBase]:
    """Полные метаданные книги по ключу. Диспатч по провайдеру."""
    if is_google_key(work_key):
        return await googlebooks_service.get_book_by_key(work_key)
    return await openlibrary_service.get_book_by_key(work_key)
