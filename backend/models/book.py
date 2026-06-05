from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BookBase(BaseModel):
    """Базовая модель книги (Open Library)."""
    work_key: str                       # стабильный id произведения, напр. "OL45804W"
    title: str
    authors: list[str] = []
    year: Optional[int] = None
    subjects: list[str] = []            # жанры/темы из Open Library
    description: Optional[str] = None
    cover_url: Optional[str] = None
    rating: Optional[float] = None


class Book(BookBase):
    """Книга из базы данных."""
    id: int
    is_read: bool = False               # аналог is_watched у фильмов
    source: str = "personal"
    rec_source: Optional[str] = None
    rec_note: Optional[str] = None
    in_library: bool = True
    user_rating: Optional[float] = None  # личная оценка 1–5 (дневник)
    user_note: Optional[str] = None      # личная заметка/отзыв
    read_at: Optional[datetime] = None   # когда отмечена прочитанной (ставится автоматически)
    added_at: datetime


class BookCreate(BaseModel):
    """Добавление книги по work key (OL…W) или свободному названию."""
    query: str
    rec_source: Optional[str] = None
    rec_note: Optional[str] = None


class BookUpdate(BaseModel):
    is_read: Optional[bool] = None
    rec_source: Optional[str] = None
    rec_note: Optional[str] = None
    user_rating: Optional[float] = Field(None, ge=0, le=5)  # 0 — очистить оценку
    user_note: Optional[str] = None


class BookSearchResult(BaseModel):
    """Результат поиска в Open Library."""
    work_key: str
    title: str
    author: Optional[str] = None
    year: Optional[str] = None
    cover_url: Optional[str] = None


class BookPreview(BaseModel):
    """Детальный превью книги перед добавлением (без сохранения в БД)."""
    work_key: str
    title: str
    authors: list[str] = []
    year: Optional[int] = None
    subjects: list[str] = []
    description: Optional[str] = None
    cover_url: Optional[str] = None
    rating: Optional[float] = None


class BookRecommendationRequest(BaseModel):
    """Подбор книги под настроение.

    Если ``library`` задан — рекомендации строятся по нему (guest-режим);
    иначе берётся библиотека пользователя из БД.
    """
    query: str
    include_read: bool = False
    library: Optional[list[Book]] = None


class BookRecommendationResponse(BaseModel):
    books: list[Book]
    explanation: str


class BookBulkImportItem(BaseModel):
    work_key: str
    is_read: bool = False
    rec_source: Optional[str] = None
    rec_note: Optional[str] = None
    source: Optional[str] = "personal"


class BookBulkImportRequest(BaseModel):
    items: list[BookBulkImportItem]
