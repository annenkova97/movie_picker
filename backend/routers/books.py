from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from typing import Optional
import re

from backend import database as db
from backend.auth import get_current_user, get_current_user_optional
from backend.models import (
    Book,
    BookCreate,
    BookUpdate,
    BookSearchResult,
    BookPreview,
    BookRecommendationRequest,
    BookRecommendationResponse,
    BookBulkImportRequest,
    User,
)
from backend.rate_limit import limiter, user_or_ip_key
from backend.services import openlibrary_service, llm_service

router = APIRouter(prefix="/api/books", tags=["books"])

_WORK_KEY_RE = re.compile(r"^OL\d+W$", re.IGNORECASE)


# ----- static sub-paths (declared before /{book_id} so они не перехватываются) -----


@router.get("/search", response_model=list[BookSearchResult])
@limiter.limit("60/minute")
async def search_books(
    request: Request,
    q: str = Query(..., min_length=1, description="Название или автор"),
):
    """Поиск книг в Open Library. Публичный, без сохранения."""
    return await openlibrary_service.search_books(q)


@router.get("/preview/{work_key}", response_model=BookPreview)
@limiter.limit("60/minute")
async def get_book_preview(request: Request, work_key: str):
    """Детальный превью книги по work key — без сохранения в БД."""
    book = await openlibrary_service.get_book_by_key(work_key)
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return BookPreview(
        work_key=book.work_key,
        title=book.title,
        authors=book.authors,
        year=book.year,
        subjects=book.subjects,
        description=book.description,
        cover_url=book.cover_url,
        rating=book.rating,
    )


@router.post("/recommend", response_model=BookRecommendationResponse)
@limiter.limit("30/hour", key_func=user_or_ip_key)
async def recommend_books(
    request: Request,
    payload: BookRecommendationRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Подбор книги под настроение (аналог /api/recommend для фильмов)."""
    if payload.library is not None:
        books = payload.library
        if not payload.include_read:
            books = [b for b in books if not b.is_read]
    elif current_user is not None:
        if payload.include_read:
            books = await db.get_all_books(user_id=current_user.id)
        else:
            books = await db.get_unread_books(user_id=current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Передай библиотеку в поле 'library' или войди в аккаунт",
        )

    if not books:
        return BookRecommendationResponse(
            books=[],
            explanation="В вашем списке пока нет книг. Сохраните хотя бы одну — тогда смогу подобрать.",
        )

    recommended_ids, explanation = await llm_service.recommend_books(
        payload.query, books, max_recommendations=3
    )
    recommended = [b for b in books if b.id in recommended_ids]
    order = {id_: idx for idx, id_ in enumerate(recommended_ids)}
    recommended.sort(key=lambda b: order.get(b.id, 999))
    return BookRecommendationResponse(books=recommended, explanation=explanation)


@router.post("/bulk-import", response_model=list[Book])
async def bulk_import_books(
    payload: BookBulkImportRequest,
    current_user: User = Depends(get_current_user),
):
    """Импорт книг в библиотеку (миграция гостевого localStorage в аккаунт).

    Идемпотентен по ``(user_id, work_key)``; неизвестные Open Library ключи
    пропускаются без ошибки.
    """
    imported: list[Book] = []
    for item in payload.items:
        existing = await db.get_user_book_by_work_key(item.work_key, current_user.id)
        if existing:
            updated = await db.update_book(
                existing.id, user_id=current_user.id, is_read=item.is_read, in_library=True
            )
            imported.append(updated or existing)
            continue

        book_base = await openlibrary_service.get_book_by_key(item.work_key)
        if not book_base:
            continue

        new_row = await db.add_book(
            book_base,
            user_id=current_user.id,
            source=item.source or "personal",
            rec_source=item.rec_source,
            rec_note=item.rec_note,
        )
        if item.is_read:
            new_row = await db.update_book(new_row.id, user_id=current_user.id, is_read=True)
        imported.append(new_row)
    return imported


@router.post("/by-key/{work_key}", response_model=Book)
async def add_book_by_key(work_key: str, current_user: User = Depends(get_current_user)):
    """Добавить книгу в библиотеку пользователя по work key."""
    existing = await db.get_user_book_by_work_key(work_key, current_user.id)
    if existing:
        return existing
    book_base = await openlibrary_service.get_book_by_key(work_key)
    if not book_base:
        raise HTTPException(status_code=404, detail=f"Книга {work_key} не найдена")
    return await db.add_book(book_base, user_id=current_user.id, source="personal")


# ----- collection -----


@router.get("", response_model=list[Book])
async def get_books(
    source: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    in_library: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Книги текущего пользователя."""
    return await db.get_all_books(
        user_id=current_user.id, source=source, is_read=is_read, in_library=in_library
    )


@router.post("", response_model=Book)
async def add_book(book_data: BookCreate, current_user: User = Depends(get_current_user)):
    """Добавить книгу по work key (OL…W) или свободному названию."""
    query = book_data.query.strip()
    if _WORK_KEY_RE.match(query):
        book_base = await openlibrary_service.get_book_by_key(query)
    else:
        results = await openlibrary_service.search_books(query)
        book_base = (
            await openlibrary_service.get_book_by_key(results[0].work_key)
            if results else None
        )

    if not book_base:
        raise HTTPException(
            status_code=404,
            detail=f"Ничего похожего на «{query}» не нашли. Попробуй уточнить название.",
        )

    existing = await db.get_user_book_by_work_key(book_base.work_key, current_user.id)
    if existing:
        raise HTTPException(
            status_code=400, detail=f"Книга '{book_base.title}' уже есть у вас в списке"
        )

    return await db.add_book(
        book_base,
        user_id=current_user.id,
        source="personal",
        rec_source=book_data.rec_source,
        rec_note=book_data.rec_note,
    )


@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: int, current_user: User = Depends(get_current_user)):
    book = await db.get_user_book_by_id(book_id, current_user.id)
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return book


@router.patch("/{book_id}", response_model=Book)
async def update_book(
    book_id: int,
    update: BookUpdate,
    current_user: User = Depends(get_current_user),
):
    book = await db.get_user_book_by_id(book_id, current_user.id)
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    if update.is_read is None and update.rec_source is None and update.rec_note is None:
        return book
    return await db.update_book(
        book_id,
        user_id=current_user.id,
        is_read=update.is_read,
        rec_source=update.rec_source,
        rec_note=update.rec_note,
    )


@router.delete("/{book_id}")
async def delete_book(book_id: int, current_user: User = Depends(get_current_user)):
    success = await db.delete_book(book_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return {"message": "Книга удалена"}
