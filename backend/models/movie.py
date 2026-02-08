from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MovieBase(BaseModel):
    """Базовая модель фильма"""
    imdb_id: str
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    genres: list[str] = []
    description: Optional[str] = None  # Краткое описание от LLM
    plot: Optional[str] = None  # Полный сюжет из OMDB
    cast: list[str] = []
    director: Optional[str] = None
    poster_url: Optional[str] = None
    imdb_rating: Optional[float] = None
    awards: Optional[str] = None


class Movie(MovieBase):
    """Фильм из базы данных"""
    id: int
    is_watched: bool = False
    source: str = "personal"  # personal / top100 / awards
    added_at: datetime


class MovieCreate(BaseModel):
    """Модель для добавления фильма по названию или IMDb ID"""
    query: str  # Название или IMDb ID (tt1234567)


class MovieUpdate(BaseModel):
    """Модель для обновления фильма"""
    is_watched: Optional[bool] = None


class RecommendationRequest(BaseModel):
    """Запрос на рекомендацию"""
    query: str  # "что-то лёгкое", "драма", "с Камбербэтчем"
    include_watched: bool = False


class RecommendationResponse(BaseModel):
    """Ответ с рекомендациями"""
    movies: list[Movie]
    explanation: str  # Почему эти фильмы подходят


class OMDBSearchResult(BaseModel):
    """Результат поиска в OMDB"""
    imdb_id: str
    title: str
    year: str
    poster_url: Optional[str] = None
