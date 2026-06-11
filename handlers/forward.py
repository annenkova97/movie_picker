"""Разбор «постов» в любом виде — фильмы И книги из любого формата сообщения.

Единый пайплайн ``_process_post`` обслуживает четыре входа:
  - пересланный пост из канала/чата (текст или фото с подписью);
  - просто фото, отправленное в чат (постер/кадр — vision-путь);
  - длинный вставленный текст (скопированный пост) — см. ``looks_like_post``;
  - ссылка на пост t.me (текст поста забираем через публичный embed).

Текст разбираем единым экстрактором ``extract_media`` (фильмы + книги). Для
фото оставляем vision-пайплайн ``extract_movies`` (он распознаёт постеры и
кадры), книги дополнительно вытаскиваем из подписи.

Фильмы резолвим через OMDB (``resolve_movies``), книги — через Google Books/
Open Library (``resolve_books``). Если нашёлся единственный фильм — сохраняем
его сразу (кнопки «Не тот» / «Не добавлять» позволяют откатить); если
несколько — уточняем, какой сохранить, кнопкой «Добавить» под каждым.

Источник рекомендации: telegram — для пересланных из каналов и t.me-ссылок
(с ссылкой на пост, когда канал публичный); для простого фото/вставленного
текста источник неизвестен и не пишется.
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
from backend.services import telegram_reader
from handlers.callbacks import auto_add_movie, wrong_undo_keyboard
from handlers.formatting import imdb_suffix
from handlers.source_context import remember_source

TELEGRAM_POST_URL_RE = telegram_reader.TELEGRAM_URL_PATTERN


def looks_like_post(text: str) -> bool:
    """Эвристика «это вставленный пост, а не название/запрос».

    Название фильма или запрос на рекомендацию — одна короткая строка; пост —
    несколько строк или длинный абзац. Порог сознательно консервативный, чтобы
    не отнимать у поиска обычные названия.
    """
    text = (text or "").strip()
    return "\n" in text or len(text) > 200


def _origin_post_url(msg) -> str | None:
    """Ссылка на оригинальный пост, если переслано из публичного канала.

    Для приватных каналов и пересылок от людей username нет — возвращаем None
    (источник тогда сохраняется без ссылки).
    """
    origin = getattr(msg, "forward_origin", None)
    chat = getattr(origin, "chat", None)
    username = getattr(chat, "username", None)
    message_id = getattr(origin, "message_id", None)
    if username and message_id:
        return f"https://t.me/{username}/{message_id}"
    return None


def _origin_rec_source(msg) -> str | None:
    """telegram — если переслано из канала/чата; None — от человека или не
    пересылка (источник рекомендации неизвестен, не выдумываем)."""
    origin = getattr(msg, "forward_origin", None)
    if getattr(origin, "chat", None) is not None:
        return "telegram"
    return None


async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересланные посты и просто фото в чат — общий вход пайплайна."""
    msg = update.message
    if msg is None:
        return

    text = (msg.text or msg.caption or "").strip()
    photo_sizes = msg.photo or ()

    if not text and not photo_sizes:
        # Голый стикер/опрос/видео — извлекать нечего, не шумим.
        return

    is_forwarded = getattr(msg, "forward_origin", None) is not None
    if is_forwarded:
        status_text = "Разбираю пересланный пост... Это может занять до минуты."
    elif photo_sizes:
        status_text = "Разбираю фото... Это может занять до минуты."
    else:
        status_text = "Разбираю текст... Это может занять до минуты."

    await _process_post(
        update, context,
        text=text,
        photo_sizes=photo_sizes,
        rec_source=_origin_rec_source(msg),
        post_url=_origin_post_url(msg),
        status_text=status_text,
    )


async def telegram_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ссылка на пост t.me, отправленная текстом: читаем пост через публичный
    embed и прогоняем через общий пайплайн с источником telegram."""
    msg = update.message
    if msg is None:
        return

    match = TELEGRAM_POST_URL_RE.search(msg.text or "")
    if not match:
        return
    url = match.group(0)

    status_msg = await msg.reply_text("Читаю пост из Telegram...")
    try:
        loop = asyncio.get_event_loop()
        post = await loop.run_in_executor(None, telegram_reader.fetch_post, url)
    except telegram_reader.TelegramReaderError as exc:
        await status_msg.edit_text(f"Не получилось открыть пост: {exc}")
        return

    await _process_post(
        update, context,
        text=post.text,
        photo_sizes=(),
        rec_source="telegram",
        post_url=post.url,
        status_msg=status_msg,
    )


async def process_pasted_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Длинный вставленный текст из ``text_handler`` — пост без источника."""
    await _process_post(
        update, context,
        text=update.message.text.strip(),
        photo_sizes=(),
        rec_source=None,
        post_url=None,
        status_text="Похоже на пост — разбираю... Это может занять до минуты.",
    )


async def _process_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    text: str,
    photo_sizes,
    rec_source: str | None,
    post_url: str | None,
    status_text: str | None = None,
    status_msg=None,
) -> None:
    """Общий пайплайн: извлечь фильмы/книги → зарезолвить → карточки/авто-сейв."""
    msg = update.message
    if status_msg is None:
        status_msg = await msg.reply_text(status_text or "Разбираю...")

    chat_id = update.effective_chat.id
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
            await resolve_movies(films_info, log_tag="post") if films_info else ([], [])
        )
        resolved_books, unmatched_books = (
            await resolve_books(books_info, log_tag="post") if books_info else ([], [])
        )

        unmatched = unmatched_movies + unmatched_books
        if unmatched:
            await msg.reply_text(
                "Не получилось найти: " + ", ".join(f"«{t}»" for t in unmatched)
            )

        total = len(resolved_movies) + len(resolved_books)
        if not total:
            await status_msg.edit_text("Не нашла ни фильмов, ни книг в этом посте.")
            return

        # Единственный фильм (и ничего больше) — сохраняем сразу.
        if len(resolved_movies) == 1 and not resolved_books:
            movie_base = resolved_movies[0]
            if rec_source:
                remember_source(chat_id, movie_base.imdb_id, rec_source, post_url)
            movie, existed = await auto_add_movie(
                msg, context, update.effective_user, movie_base,
                rec_source=rec_source, source_url=post_url,
            )
            await _send_movie_card(
                msg, movie,
                post_url=post_url,
                saved_note="✔️ Уже в твоём списке." if existed
                else "✅ Сохранила в твой список.",
                keyboard=None if existed else wrong_undo_keyboard(movie.id),
            )
            await status_msg.edit_text(
                "Этот фильм уже в твоём списке 👇" if existed
                else "Нашла фильм и сразу сохранила 👇"
            )
            return

        for movie in resolved_movies:
            if rec_source:
                remember_source(chat_id, movie.imdb_id, rec_source, post_url)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Добавить", callback_data=f"add:{movie.imdb_id}")]
            ])
            await _send_movie_card(msg, movie, post_url=post_url, keyboard=keyboard)
        for book in resolved_books:
            if rec_source:
                remember_source(chat_id, book.work_key, rec_source, post_url)
            await _send_book_card(msg, book)

        await status_msg.edit_text(
            "Нашла несколько похожих вариантов. Уточни, какой сохранить?"
            if total > 1
            else "Готово! Нажми «Добавить», если хочешь сохранить."
        )

    except Exception as exc:
        print(f"[post_handler] ERROR: {traceback.format_exc()}", flush=True)
        await status_msg.edit_text(f"Ошибка: {type(exc).__name__}: {exc}"[:4000])
    finally:
        if frame_paths:
            cleanup_temp_files(frame_paths)


async def _send_movie_card(
    reply_to, movie, *, post_url: str | None = None,
    saved_note: str | None = None, keyboard=None,
) -> None:
    """Карточка фильма: название, рейтинг, описание, ссылка на пост-источник."""
    rating = imdb_suffix(getattr(movie, "imdb_rating", None), "  ★ ")
    lines = [f"*{movie.title}* ({movie.year}){rating}"]
    if movie.description:
        lines.append(f"_{movie.description}_")
    if post_url:
        lines.append("")
        lines.append(f"📢 из [Telegram]({post_url})")
    if saved_note:
        lines.append("")
        lines.append(saved_note)
    text = "\n".join(lines)

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
