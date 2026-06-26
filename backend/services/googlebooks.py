"""Google Books client — основной поисковик книг.

Open Library англоцентричен и плохо находит русскоязычные книги (запрос
«Бродский» почти ничего не даёт). Google Books знает русский каталог
заметно лучше: умеет ``langRestrict=ru`` и поиск по автору ``inauthor:``.

Интерфейс намеренно совпадает с ``services/openlibrary.py`` — оба отдают
``BookSearchResult`` / ``BookBase``, так что диспетчер ``book_search`` может
выбирать провайдера прозрачно.

Идентификатор тома Google Books хранится как ``gb:<volumeId>`` (ключи Open
Library остаются ``OL…W``), чтобы по префиксу понимать, куда идти за деталями.
Без ключа API работает (анонимная квота); ключ — ``GOOGLE_BOOKS_API_KEY``.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from backend.config import GOOGLE_BOOKS_API_KEY, GOOGLE_BOOKS_BASE_URL
from backend.models.book import BookBase, BookSearchResult

log = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0)
_PREFIX = "gb:"


def _strip_prefix(work_key: str) -> str:
    """'gb:zyTCAlFPjgYC' → 'zyTCAlFPjgYC'. Idempotent for bare ids."""
    return work_key[len(_PREFIX):] if work_key.startswith(_PREFIX) else work_key


def _year(published_date) -> Optional[int]:
    """Достаём 4-значный год из 'YYYY', 'YYYY-MM', 'YYYY-MM-DD'."""
    if not published_date:
        return None
    m = re.search(r"\d{4}", str(published_date))
    return int(m.group()) if m else None


def _cover(image_links: Optional[dict]) -> Optional[str]:
    if not image_links:
        return None
    url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
    if not url:
        return None
    # Google отдаёт http и иногда с &edge=curl (загнутый угол) — чистим.
    url = url.replace("http://", "https://").replace("&edge=curl", "")
    return url


def _params(extra: dict) -> dict:
    params = dict(extra)
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
    return params


class GoogleBooksService:
    """Сервис поиска книг через Google Books."""

    async def search_books(
        self, query: str, prefer_lang: Optional[str] = None
    ) -> list[BookSearchResult]:
        """Поиск книг. ``prefer_lang='ru'`` ограничивает выдачу русским языком.

        Сетевые/квотные ошибки гасятся в пустой список, чтобы диспетчер мог
        откатиться на Open Library, а не падать.
        """
        params: dict = {"q": query, "maxResults": "20"}
        if prefer_lang:
            params["langRestrict"] = prefer_lang
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(GOOGLE_BOOKS_BASE_URL, params=_params(params))
                if resp.status_code != 200:
                    # 429 здесь почти всегда = исчерпана АНОНИМНАЯ квота (нет
                    # GOOGLE_BOOKS_API_KEY): русский поиск держится на Google,
                    # так что молча отдавать [] = «ничего не найдено» для юзера.
                    # Логируем, чтобы причина была видна в проде, а не гадалась.
                    level = logging.WARNING if resp.status_code == 429 else logging.INFO
                    log.log(
                        level,
                        "Google Books %s for q=%r (langRestrict=%s)%s",
                        resp.status_code, query, prefer_lang or "-",
                        " — quota exceeded; set GOOGLE_BOOKS_API_KEY"
                        if resp.status_code == 429 else "",
                    )
                    return []
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Google Books request failed for q=%r: %s", query, exc)
            return []

        results: list[BookSearchResult] = []
        for item in data.get("items", []):
            volume_id = item.get("id")
            info = item.get("volumeInfo") or {}
            title = info.get("title")
            if not volume_id or not title:
                continue
            authors = info.get("authors") or []
            results.append(BookSearchResult(
                work_key=f"{_PREFIX}{volume_id}",
                title=title,
                author=", ".join(authors[:2]) if authors else None,
                year=str(_year(info.get("publishedDate"))) if info.get("publishedDate") else None,
                cover_url=_cover(info.get("imageLinks")),
            ))
        return results

    async def get_book_by_key(self, work_key: str) -> Optional[BookBase]:
        """Полные метаданные тома по ``gb:<volumeId>`` (или голому id)."""
        volume_id = _strip_prefix(work_key)
        url = f"{GOOGLE_BOOKS_BASE_URL}/{volume_id}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url, params=_params({}))
                if resp.status_code != 200:
                    return None
                item = resp.json()
        except (httpx.HTTPError, ValueError):
            return None

        info = item.get("volumeInfo") or {}
        title = info.get("title")
        if not title:
            return None
        return BookBase(
            work_key=f"{_PREFIX}{volume_id}",
            title=title,
            authors=(info.get("authors") or [])[:3],
            year=_year(info.get("publishedDate")),
            subjects=(info.get("categories") or [])[:8],
            description=info.get("description"),
            cover_url=_cover(info.get("imageLinks")),
            rating=info.get("averageRating"),
        )


def is_google_key(work_key: str) -> bool:
    return bool(work_key) and work_key.startswith(_PREFIX)


googlebooks_service = GoogleBooksService()
