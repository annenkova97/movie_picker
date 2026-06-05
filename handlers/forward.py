"""Парсинг пересланных постов из Telegram-каналов — фильмы И книги.

Текстовые посты разбираем единым экстрактором ``extract_media`` (фильмы +
книги). Для постов с фото оставляем vision-пайплайн ``extract_movies`` (он
распознаёт постеры/кадры), а книги дополнительно вытаскиваем из подписи.

Фильмы резолвим через OMDB (``resolve_movies``), книги — через Google Books/
Open Library (``resolve_books``). Под каждой карточкой кнопка «Добавить».
"""

from __future__ import annotations

import asyncio
import traceback
import uuid
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from backend.config import INSTAGRAM_TEMP_DIR
from backend.services.instagram_reader import cleanup_temp_files, extract_movies
from backend.services.media_extractor import extract_media
from backend.services.movie_resolver import resolve_movies
from backend.services.book_resolver import resolve_books


async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Извлекает фильмы и книги из пересланного сообщения и предлагает добавить."""
    msg = update.message
    if msg is None:
        return

    text = (msg.text or msg.caption or "").strip()
    photo_sizes = msg.photo or ()

    if not text and not photo_sizes:
        # Голый стикер/опрос/видео — извлекать нечего, не шумим.
        return

    status_msg = await msg.reply_text(
        "Разбираю пересланный пост... Это может занять до минуты."
    )

    frame_paths: list[str] = []
    try:
        films_info = []
        books_info = []

        if photo_sizes:
            # Vision-путь для фильмов (постер/кадр), книги — из подписи.
            tg_file = await photo_sizes[-1].get_file()
            photo_path = Path(INSTAGRAM_TEMP_DIR) / f"forward_{uuid.uuid4().hex}.jpg"
            await tg_file.download_to_drive(custom_path=str(photo_path))
            frame_paths.append(str(photo_path))

            loop = asyncio.get_event_loop()
            films_info = await loop.run_in_executor(
                None, extract_movies, "", text, frame_paths, True,
            )
            if text:
                _, books_info = await extract_media(text)
        else:
            films_info, books_info = await extract_media(text)

        resolved_movies, unmatched_movies = (
            await resolve_movies(films_info, log_tag="forward") if films_info else ([], [])
        )
        resolved_books, unmatched_books = (
            await resolve_books(books_info, log_tag="forward") if books_info else ([], [])
        )

        for movie in resolved_movies:
            await _send_movie_card(msg, movie)
        for book in resolved_books:
            await _send_book_card(msg, book)

        unmatched = unmatched_movies + unmatched_books
        if unmatched:
            await msg.reply_text(
                "Не получилось найти: " + ", ".join(f"«{t}»" for t in unmatched)
            )

        total = len(resolved_movies) + len(resolved_books)
        if total:
            await status_msg.edit_text(
                f"Готово! Нашёл {total}. Нажми «Добавить» под нужными."
            )
        else:
            await status_msg.edit_text("Не нашёл ни фильмов, ни книг в этом посте.")

    except Exception as exc:
        print(f"[forward_handler] ERROR: {traceback.format_exc()}", flush=True)
        await status_msg.edit_text(f"Ошибка: {type(exc).__name__}: {exc}"[:4000])
    finally:
        if frame_paths:
            cleanup_temp_files(frame_paths)


async def _send_movie_card(reply_to, movie) -> None:
    """Карточка фильма с кнопкой «Добавить»."""
    lines = [f"*{movie.title}* ({movie.year})"]
    if movie.description:
        lines.append(f"_{movie.description}_")
    text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Добавить в список", callback_data=f"add:{movie.imdb_id}")]
    ])

    if movie.poster_url:
        try:
            await reply_to.reply_photo(
                photo=movie.poster_url, caption=text,
                parse_mode="Markdown", reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    await reply_to.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def _send_book_card(reply_to, book) -> None:
    """Карточка книги с кнопкой «Добавить книгу»."""
    author = ", ".join(book.authors[:2]) if book.authors else ""
    head = f"📖 *{book.title}*"
    if book.year:
        head += f" ({book.year})"
    lines = [head]
    if author:
        lines.append(f"_{author}_")
    text = "\n".join(lines)

    # work_key может быть "gb:<id>" — callback_handler режет по первому ":",
    # так что action="addbook", value="gb:<id>" сохраняется целиком.
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Добавить книгу", callback_data=f"addbook:{book.work_key}")]
    ])

    if book.cover_url:
        try:
            await reply_to.reply_photo(
                photo=book.cover_url, caption=text,
                parse_mode="Markdown", reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    await reply_to.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
