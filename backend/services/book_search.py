"""Единая точка поиска книг: Google Books → Open Library (фолбэк).

Зеркало ``services/title_search.py`` для фильмов. Google Books идёт первым —
он сильно лучше находит русскоязычные книги (для кириллицы добавляем
``langRestrict=ru``). Если Google ничего не вернул или упал по квоте —
откатываемся на Open Library.

Детали тянем по префиксу ключа: ``gb:…`` → Google Books, ``OL…W`` → Open Library.
"""

from __future__ import annotations

from typing import Optional

from backend.models.book import BookBase, BookSearchResult
from backend.services.googlebooks import googlebooks_service, is_google_key
from backend.services.openlibrary import openlibrary_service
from backend.services.title_search import has_cyrillic


async def search_books(query: str) -> list[BookSearchResult]:
    """Карточки книг для UI. Google Books первым, Open Library — фолбэк."""
    query = query.strip()
    if not query:
        return []

    prefer_lang = "ru" if has_cyrillic(query) else None
    results = await googlebooks_service.search_books(query, prefer_lang=prefer_lang)
    if results:
        return results

    return await openlibrary_service.search_books(query)


async def get_book_by_key(work_key: str) -> Optional[BookBase]:
    """Полные метаданные книги по ключу. Диспатч по провайдеру."""
    if is_google_key(work_key):
        return await googlebooks_service.get_book_by_key(work_key)
    return await openlibrary_service.get_book_by_key(work_key)
