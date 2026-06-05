"""TMDB (The Movie Database) — русскоязычный поиск фильмов И сериалов.

OMDB — англоязычный, кириллический запрос там почти ничего не найдёт, а
сериалы по русскому названию он не находит вовсе. TMDB официально поддерживает
любой язык через ``language=ru-RU`` и хорошо покрывает международные и
российские фильмы И сериалы (с русскими названиями).

Что делаем:
1. Поиск ``/search/movie`` или ``/search/tv`` (``language=ru-RU``) → TMDB id'ы.
2. Для каждого хита достаём IMDb id — без него мы не свяжем запись с остальным
   пайплайном (OMDB-метадата, add-кнопка, библиотека). У фильма imdb_id лежит
   в деталях ``/movie/{id}``, у сериала — в ``/tv/{id}/external_ids``.
3. Конвертируем в ``OMDBSearchResult`` — стандартный «карточный» формат.

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
# берём top-N. Лимит держим небольшим, чтобы не делать слишком много
# follow-up'ов за imdb_id.
_MAX_SEARCH_RESULTS = 5
_TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"

# Movie и TV отличаются именами полей и тем, откуда брать imdb_id. Держим эти
# различия в одном месте, чтобы логика поиска (``_search``) оставалась общей.
_KIND = {
    "movie": {
        "search_path": "/search/movie",
        "title_keys": ("title", "original_title"),
        "date_key": "release_date",
        # imdb_id лежит прямо в корне ответа /movie/{id}.
        "imdb_path": "/movie/{id}",
    },
    "tv": {
        "search_path": "/search/tv",
        "title_keys": ("name", "original_name"),
        "date_key": "first_air_date",
        # у сериалов imdb_id отдаёт только отдельная ручка external_ids.
        "imdb_path": "/tv/{id}/external_ids",
    },
}


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
        """Ищет фильмы (back-compat: исходная сигнатура сервиса)."""
        return await self._search(query, "movie", language=language)

    async def search_tv(
        self, query: str, *, language: str = "ru-RU",
    ) -> list[OMDBSearchResult]:
        """Ищет сериалы. TMDb знает русские названия сериалов, а OMDB по
        кириллице их не находит вообще — это «другое место» для сериалов."""
        return await self._search(query, "tv", language=language)

    async def search_any(
        self, query: str, *, language: str = "ru-RU",
    ) -> list[OMDBSearchResult]:
        """Фильмы + сериалы одним вызовом: фильмы первыми, дедуп по imdb_id."""
        movies = await self.search(query, language=language)
        tv = await self.search_tv(query, language=language)

        seen = {r.imdb_id for r in movies}
        merged = list(movies)
        for r in tv:
            if r.imdb_id not in seen:
                seen.add(r.imdb_id)
                merged.append(r)
        return merged

    async def _search(
        self, query: str, kind: str, *, language: str,
    ) -> list[OMDBSearchResult]:
        """Общая логика поиска для фильмов и сериалов (различия — в ``_KIND``)."""
        if not self.enabled or not query.strip():
            return []

        cfg = _KIND[kind]

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                search_resp = await client.get(
                    f"{self.base_url}{cfg['search_path']}",
                    params={
                        "api_key": self.api_key,
                        "query": query,
                        "language": language,
                        "include_adult": "false",
                    },
                )
                search_resp.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"[tmdb] {kind} search failed: {exc}")
                return []

            payload = search_resp.json() or {}
            # TMDB сортирует по релевантности; берём верхушку.
            hits = [h for h in (payload.get("results") or []) if h.get("id")]
            hits = hits[:_MAX_SEARCH_RESULTS]
            if not hits:
                return []

            # Параллельно тянем imdb_id — N маленьких запросов быстрее цепочки.
            imdb_ids = await asyncio.gather(*[
                self._fetch_imdb_id(client, hit["id"], cfg["imdb_path"])
                for hit in hits
            ])

        results: list[OMDBSearchResult] = []
        for hit, imdb_id in zip(hits, imdb_ids):
            if not imdb_id:
                # Без IMDb id фильм/сериал не добавить в библиотеку через
                # нашу OMDB-схему — пропускаем.
                continue

            title = next((hit.get(k) for k in cfg["title_keys"] if hit.get(k)), "")
            date = hit.get(cfg["date_key"]) or ""
            poster_path = hit.get("poster_path")
            poster_url = f"{_TMDB_POSTER_BASE}{poster_path}" if poster_path else None

            results.append(OMDBSearchResult(
                imdb_id=imdb_id,
                title=title,
                year=date[:4] if date else "",
                poster_url=poster_url,
            ))

        return results

    async def _fetch_imdb_id(
        self, client: httpx.AsyncClient, tmdb_id: int, imdb_path: str,
    ) -> str | None:
        """Достаёт imdb_id (вида ``tt1234567``) из детальной ручки TMDb."""
        try:
            resp = await client.get(
                f"{self.base_url}{imdb_path.format(id=tmdb_id)}",
                params={"api_key": self.api_key},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"[tmdb] imdb id fetch failed for {tmdb_id}: {exc}")
            return None

        # TMDB иногда отдаёт пустую строку — нормализуем в None.
        return (resp.json() or {}).get("imdb_id") or None


tmdb_service = TMDBService()
