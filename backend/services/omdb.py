import re
import time
import httpx
from typing import Optional
from backend.config import OMDB_API_KEY, OMDB_BASE_URL
from backend.models.movie import MovieBase, OMDBSearchResult


class OMDBService:
    """Сервис для работы с OMDB API"""

    # Детали фильма по IMDb ID практически не меняются — суток кэша достаточно,
    # чтобы один и тот же фильм, сохраняемый разными людьми, не бил по OMDB
    # повторно (и не съедал дневной лимит). Поиск меняется чаще (новые релизы
    # индексируются), но за час — нет; часовой кэш гасит повторные запросы
    # «одно и то же название» от разных людей и ретраев.
    _BY_ID_TTL = 24 * 3600
    _SEARCH_TTL = 3600
    _SEARCH_CACHE_MAX = 500

    def __init__(self):
        self.api_key = OMDB_API_KEY
        self.base_url = OMDB_BASE_URL
        self._by_id_cache: dict[str, tuple[float, MovieBase]] = {}
        self._search_cache: dict[str, tuple[float, list[OMDBSearchResult]]] = {}

    async def search_movies(self, query: str, media_type: str = "movie") -> list[OMDBSearchResult]:
        """Поиск фильмов по названию (с часовым кэшем)."""
        cache_key = f"{media_type}|{query.strip().lower()}"
        cached = self._search_cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < self._SEARCH_TTL:
            return list(cached[1])

        params: dict = {
            "apikey": self.api_key,
            "s": query,
        }
        if media_type:
            params["type"] = media_type

        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            data = response.json()

            results = []
            # Промахи тоже кэшируем: повторный поиск несуществующего названия —
            # самый частый источник лишних запросов к OMDB.
            found = data.get("Search", []) if data.get("Response") != "False" else []
            for item in found:
                results.append(OMDBSearchResult(
                    imdb_id=item.get("imdbID", ""),
                    title=item.get("Title", ""),
                    year=item.get("Year", ""),
                    poster_url=item.get("Poster") if item.get("Poster") != "N/A" else None
                ))

        if len(self._search_cache) >= self._SEARCH_CACHE_MAX:
            self._search_cache.clear()  # примитивно, но кэш — только щит от лимита
        self._search_cache[cache_key] = (time.monotonic(), results)
        return list(results)

    async def get_movie_by_id(self, imdb_id: str) -> Optional[MovieBase]:
        """Получить детали фильма по IMDb ID (с кэшем на сутки).

        Возвращаем копию (``model_copy``), потому что вызывающие иногда
        дописывают поля (например, ``description``) — оригинал в кэше трогать
        нельзя.
        """
        cached = self._by_id_cache.get(imdb_id)
        if cached and (time.monotonic() - cached[0]) < self._BY_ID_TTL:
            return cached[1].model_copy(deep=True)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "apikey": self.api_key,
                    "i": imdb_id,
                    "plot": "full"
                }
            )
            data = response.json()

            if data.get("Response") == "False":
                return None

            movie = self._parse_movie(data)

        self._by_id_cache[imdb_id] = (time.monotonic(), movie)
        return movie.model_copy(deep=True)

    async def get_movie_by_title(self, title: str, year: Optional[int] = None) -> Optional[MovieBase]:
        """Получить детали фильма по названию"""
        async with httpx.AsyncClient() as client:
            params = {
                "apikey": self.api_key,
                "t": title,
                "plot": "full"
            }
            if year:
                params["y"] = year

            response = await client.get(self.base_url, params=params)
            data = response.json()

            if data.get("Response") == "False":
                return None

            return self._parse_movie(data)

    def _parse_movie(self, data: dict) -> MovieBase:
        """Преобразование ответа OMDB в модель MovieBase"""
        # Парсинг жанров
        genres = []
        if data.get("Genre") and data["Genre"] != "N/A":
            genres = [g.strip() for g in data["Genre"].split(",")]

        # Парсинг актёров
        cast = []
        if data.get("Actors") and data["Actors"] != "N/A":
            cast = [a.strip() for a in data["Actors"].split(",")]

        # Парсинг рейтинга
        imdb_rating = None
        if data.get("imdbRating") and data["imdbRating"] != "N/A":
            try:
                imdb_rating = float(data["imdbRating"])
            except ValueError:
                pass

        # Парсинг года
        year = None
        if data.get("Year") and data["Year"] != "N/A":
            try:
                # OMDB может вернуть "2010–2015" для сериалов
                year = int(data["Year"].split("–")[0])
            except ValueError:
                pass

        # OMDB отдаёт "Type": movie / series / episode / game. Сериалы и их
        # эпизоды кладём в категорию «сериалы», всё остальное — «фильмы».
        media_type = "series" if (data.get("Type") or "").lower() in (
            "series", "episode",
        ) else "movie"

        # "Runtime": "148 min" → 148. Для сериалов это длительность эпизода.
        # 0 — OMDB длительности не знает (маркер «проверено» для бэкфилла).
        runtime = 0
        raw_runtime = data.get("Runtime") or ""
        runtime_match = re.search(r"(\d+)", raw_runtime)
        if runtime_match:
            runtime = int(runtime_match.group(1))

        return MovieBase(
            imdb_id=data.get("imdbID", ""),
            title=data.get("Title", ""),
            original_title=data.get("Title"),
            year=year,
            media_type=media_type,
            genres=genres,
            plot=data.get("Plot") if data.get("Plot") != "N/A" else None,
            cast=cast,
            director=data.get("Director") if data.get("Director") != "N/A" else None,
            poster_url=data.get("Poster") if data.get("Poster") != "N/A" else None,
            imdb_rating=imdb_rating,
            awards=data.get("Awards") if data.get("Awards") != "N/A" else None,
            runtime=runtime,
        )


# Синглтон для использования в приложении
omdb_service = OMDBService()
