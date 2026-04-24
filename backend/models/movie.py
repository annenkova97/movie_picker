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
    plot_ru: Optional[str] = None  # Перевод plot на русский (кэш)
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
    rec_source: Optional[str] = None  # telegram / instagram / friends / personal
    rec_note: Optional[str] = None  # откуда пришла рекомендация ("канал Х", "Аня посоветовала")
    in_library: bool = True  # True — на полке пользователя; False — только в каталоге наград
    award: Optional[str] = None  # "Oscar Best Picture", "Palme d'Or", ...
    award_year: Optional[int] = None  # год награды (может отличаться от year выпуска)
    added_at: datetime


class MovieCreate(BaseModel):
    """Модель для добавления фильма по названию или IMDb ID"""
    query: str  # Название или IMDb ID (tt1234567)
    rec_source: Optional[str] = None  # telegram / instagram / friends / personal
    rec_note: Optional[str] = None


class MovieUpdate(BaseModel):
    """Модель для обновления фильма"""
    is_watched: Optional[bool] = None
    rec_source: Optional[str] = None
    rec_note: Optional[str] = None


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


class MoviePreview(BaseModel):
    """Детальный превью фильма для показа перед добавлением (без сохранения в БД)"""
    imdb_id: str
    title: str
    year: Optional[int] = None
    poster_url: Optional[str] = None
    imdb_rating: Optional[float] = None
    genres: list[str] = []
    plot: Optional[str] = None
    director: Optional[str] = None
    cast: list[str] = []
    awards: Optional[str] = None
