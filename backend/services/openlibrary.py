"""Open Library client — the books analogue of services/omdb.py.

Open Library is free and keyless. We use two endpoints:
  - search.json        → fast title/author search for the results list
  - works/{key}.json   → full metadata (description, subjects, authors) on add

Work keys are stored without the "/works/" prefix (e.g. "OL45804W"), mirroring
how movies use the bare IMDb id.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from backend.models.book import BookBase, BookSearchResult

log = logging.getLogger(__name__)

_SEARCH_URL = "https://openlibrary.org/search.json"
_WORKS_URL = "https://openlibrary.org/works/{key}.json"
_AUTHOR_URL = "https://openlibrary.org{key}.json"  # key already starts with /authors/...
_COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

_TIMEOUT = httpx.Timeout(10.0)


def _strip_works_prefix(key: str) -> str:
    """'/works/OL45804W' → 'OL45804W'. Idempotent for bare keys."""
    return key.rsplit("/", 1)[-1] if key else key


def _first_year(value) -> Optional[int]:
    """Pull a 4-digit year out of an int or a free-form date string."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    m = re.search(r"\d{4}", str(value))
    return int(m.group()) if m else None


def _cover_url(cover_id) -> Optional[str]:
    if not cover_id or (isinstance(cover_id, int) and cover_id < 0):
        return None
    return _COVER_URL.format(cover_id=cover_id)


class OpenLibraryService:
    """Сервис для работы с Open Library (книги)."""

    async def search_books(self, query: str) -> list[BookSearchResult]:
        """Поиск книг по названию/автору. Один запрос к search.json."""
        params = {
            "q": query,
            "limit": "12",
            "fields": "key,title,author_name,first_publish_year,cover_i",
        }
        # Open Library — это последний фолбэк под Google Books; если он лёг или
        # ответил не-200, гасим в пустой список, а не роняем весь /search в 500.
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(_SEARCH_URL, params=params)
                if resp.status_code != 200:
                    log.info("Open Library %s for q=%r", resp.status_code, query)
                    return []
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Open Library request failed for q=%r: %s", query, exc)
            return []

        results: list[BookSearchResult] = []
        for doc in data.get("docs", []):
            key = doc.get("key")
            if not key:
                continue
            authors = doc.get("author_name") or []
            year = doc.get("first_publish_year")
            results.append(BookSearchResult(
                work_key=_strip_works_prefix(key),
                title=doc.get("title", ""),
                author=", ".join(authors[:2]) if authors else None,
                year=str(year) if year else None,
                cover_url=_cover_url(doc.get("cover_i")),
            ))
        return results

    async def get_book_by_key(self, work_key: str) -> Optional[BookBase]:
        """Полные метаданные книги по work key (description, subjects, авторы)."""
        key = _strip_works_prefix(work_key)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_WORKS_URL.format(key=key))
            if resp.status_code != 200:
                return None
            work = resp.json()

            description = _parse_description(work.get("description"))
            subjects = [s for s in (work.get("subjects") or [])][:8]
            covers = [c for c in (work.get("covers") or []) if isinstance(c, int) and c > 0]
            cover_url = _cover_url(covers[0]) if covers else None
            year = _first_year(work.get("first_publish_date"))

            # Авторов резолвим отдельными вызовами (их обычно 1–2; ограничиваем 3).
            authors = await _resolve_authors(client, work.get("authors") or [])

        return BookBase(
            work_key=key,
            title=work.get("title", ""),
            authors=authors,
            year=year,
            subjects=subjects,
            description=description,
            cover_url=cover_url,
        )


def _parse_description(value) -> Optional[str]:
    """Open Library description is either a string or {type, value}."""
    if not value:
        return None
    if isinstance(value, dict):
        return value.get("value")
    return str(value)


async def _resolve_authors(client: httpx.AsyncClient, author_refs: list) -> list[str]:
    names: list[str] = []
    for ref in author_refs[:3]:
        author_key = (ref.get("author") or {}).get("key") if isinstance(ref, dict) else None
        if not author_key:
            continue
        try:
            r = await client.get(_AUTHOR_URL.format(key=author_key))
            if r.status_code == 200:
                name = r.json().get("name")
                if name:
                    names.append(name)
        except httpx.HTTPError:
            continue
    return names


# Синглтон для использования в приложении
openlibrary_service = OpenLibraryService()
