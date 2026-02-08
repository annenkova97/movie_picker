import httpx
from typing import Optional
from backend.config import OMDB_API_KEY, OMDB_BASE_URL
from backend.models.movie import MovieBase, OMDBSearchResult


class OMDBService:
    """Сервис для работы с OMDB API"""

    def __init__(self):
        self.api_key = OMDB_API_KEY
        self.base_url = OMDB_BASE_URL

    async def search_movies(self, query: str) -> list[OMDBSearchResult]:
        """Поиск фильмов по названию"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "apikey": self.api_key,
                    "s": query,
                    "type": "movie"
                }
            )
            data = response.json()

            if data.get("Response") == "False":
                return []

            results = []
            for item in data.get("Search", []):
                results.append(OMDBSearchResult(
                    imdb_id=item.get("imdbID", ""),
                    title=item.get("Title", ""),
                    year=item.get("Year", ""),
                    poster_url=item.get("Poster") if item.get("Poster") != "N/A" else None
                ))
            return results

    async def get_movie_by_id(self, imdb_id: str) -> Optional[MovieBase]:
        """Получить детали фильма по IMDb ID"""
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

            return self._parse_movie(data)

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

        return MovieBase(
            imdb_id=data.get("imdbID", ""),
            title=data.get("Title", ""),
            original_title=data.get("Title"),
            year=year,
            genres=genres,
            plot=data.get("Plot") if data.get("Plot") != "N/A" else None,
            cast=cast,
            director=data.get("Director") if data.get("Director") != "N/A" else None,
            poster_url=data.get("Poster") if data.get("Poster") != "N/A" else None,
            imdb_rating=imdb_rating,
            awards=data.get("Awards") if data.get("Awards") != "N/A" else None
        )


# Синглтон для использования в приложении
omdb_service = OMDBService()
