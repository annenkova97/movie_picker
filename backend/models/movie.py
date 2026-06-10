from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MovieBase(BaseModel):
    """Базовая модель фильма"""
    imdb_id: str
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    media_type: str = "movie"  # "movie" или "series" (для разбивки фильмы/сериалы)
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
    source_url: Optional[str] = None  # ссылка на оригинал рекомендации (Reel, пост в канале)
    in_library: bool = True  # True — на полке пользователя; False — только в каталоге наград
    award: Optional[str] = None  # "Oscar Best Picture", "Palme d'Or", ...
    award_year: Optional[int] = None  # год награды (может отличаться от year выпуска)
    user_rating: Optional[float] = None  # личная оценка 1–5 (дневник), None — не оценено
    user_note: Optional[str] = None  # личная заметка/отзыв «чтобы не забыть»
    watched_at: Optional[datetime] = None  # когда отмечен просмотренным (ставится автоматически)
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
    user_rating: Optional[float] = Field(None, ge=0, le=5)  # 0 — очистить оценку
    user_note: Optional[str] = None


class RecommendationRequest(BaseModel):
    """Запрос на рекомендацию.

    Если ``library`` задан — рекомендации строятся по нему (guest-режим, без auth).
    Если ``library`` пуст и есть auth-токен — берётся библиотека пользователя из БД.
    Если нет ни того, ни другого — рекомендация будет «холодной»: без контекста.
    """
    query: str  # "что-то лёгкое", "драма", "с Камбербэтчем"
    include_watched: bool = False
    library: Optional[list[Movie]] = None


class BulkImportItem(BaseModel):
    """Одна запись для миграции гостевой библиотеки в аккаунт."""
    imdb_id: str
    is_watched: bool = False
    rec_source: Optional[str] = None
    rec_note: Optional[str] = None
    source: Optional[str] = "personal"


class BulkImportRequest(BaseModel):
    items: list[BulkImportItem]


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
    media_type: str = "movie"  # "movie" или "series"
    poster_url: Optional[str] = None
    imdb_rating: Optional[float] = None
    genres: list[str] = []
    plot: Optional[str] = None
    director: Optional[str] = None
    cast: list[str] = []
    awards: Optional[str] = None
