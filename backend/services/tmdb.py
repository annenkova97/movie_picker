"""TMDB (The Movie Database) — русскоязычный поиск фильмов.

OMDB — англоязычный, кириллический запрос там почти ничего не найдёт.
TMDB официально поддерживает любой язык через ``language=ru-RU`` и хорошо
покрывает как международные, так и российские фильмы (с русскими названиями).

Что делаем:
1. Поиск ``/search/movie?language=ru-RU&query=...`` → получаем TMDB id'ы.
2. Для каждого хита дёргаем ``/movie/{id}`` (тоже ``language=ru-RU``), чтобы
   достать IMDb id — без него мы не сможем подтянуть полную метадату из OMDB
   и связать запись с остальным пайплайном (add-кнопка, библиотека).
3. Конвертируем в ``OMDBSearchResult`` — стандартный «карточный» формат,
   который рисуют ``/search`` и свободный текст.

Конфигурация: ``TMDB_API_KEY`` в .env. Если ключа нет — сервис тихо ничего
не возвращает, и пайплайн откатывается на OMDB+LLM-перевод.
Ключ бесплатный, выпускается на https://www.themoviedb.org/settings/api.
"""

from __future__ import annotations

import asyncio

import httpx

from backend.config import TMDB_API_KEY, TMDB_BASE_URL
from backend.models.movie import OMDBSearchResult


# TMDB иногда возвращает мусорные совпадения (порно, чужие языки и т.п.) —
# фильтруем по поп-метрике и берём top-N. Лимит держим небольшим, чтобы не
# делать слишком много follow-up'ов за imdb_id.
_MAX_SEARCH_RESULTS = 5
_TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"


class TMDBService:
    def __init__(self) -> None:
        self.api_key = TMDB_API_KEY
        self.base_url = TMDB_BASE_URL

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(
        self, query: str, *, language: str = "ru-RU",
    ) -> list[OMDBSearchResult]:
        """Ищет фильмы и возвращает результаты с IMDb id'ами (для интеграции с OMDB)."""
        if not self.enabled or not query.strip():
            return []

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                search_resp = await client.get(
                    f"{self.base_url}/search/movie",
                    params={
                        "api_key": self.api_key,
                        "query": query,
                        "language": language,
                        "include_adult": "false",
                    },
                )
                search_resp.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"[tmdb] search failed: {exc}")
                return []

            payload = search_resp.json() or {}
            hits = payload.get("results") or []
            # TMDB сортирует по релевантности, но дополнительно отсекаем
            # совсем непопулярные — там обычно мусор и дубли.
            hits = [h for h in hits if h.get("id")][:_MAX_SEARCH_RESULTS]

            if not hits:
                return []

            # Параллельно тянем детали ради imdb_id — N маленьких запросов
            # быстрее, чем последовательная цепочка.
            detail_tasks = [
                self._fetch_imdb_id(client, hit["id"], language=language)
                for hit in hits
            ]
            imdb_ids = await asyncio.gather(*detail_tasks)

        results: list[OMDBSearchResult] = []
        for hit, imdb_id in zip(hits, imdb_ids):
            if not imdb_id:
                # Без IMDb id нет смысла — мы не сможем добавить фильм в
                # библиотеку через нашу OMDB-схему.
                continue

            title = hit.get("title") or hit.get("original_title") or ""
            year = ""
            release_date = hit.get("release_date") or ""
            if release_date:
                year = release_date[:4]
            poster_path = hit.get("poster_path")
            poster_url = f"{_TMDB_POSTER_BASE}{poster_path}" if poster_path else None

            results.append(OMDBSearchResult(
                imdb_id=imdb_id,
                title=title,
                year=year,
                poster_url=poster_url,
            ))

        return results

    async def _fetch_imdb_id(
        self, client: httpx.AsyncClient, tmdb_id: int, *, language: str,
    ) -> str | None:
        """GET /movie/{id} — там лежит imdb_id (вида ``tt1234567``)."""
        try:
            resp = await client.get(
                f"{self.base_url}/movie/{tmdb_id}",
                params={"api_key": self.api_key, "language": language},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"[tmdb] detail fetch failed for {tmdb_id}: {exc}")
            return None

        imdb_id = (resp.json() or {}).get("imdb_id")
        # TMDB иногда отдаёт пустую строку — нормализуем в None.
        return imdb_id or None


tmdb_service = TMDBService()
