"""Парсинг пересланных постов из Telegram-каналов.

Поддерживает:
- текстовые посты с описанием фильма(ов);
- посты с фото (постер / кадр / актёры) — с caption или без.

Внутри переиспользуем ``extract_movies`` (тот же LLM-промпт, что для Instagram
Reel) и ``resolve_movies`` (OMDB lookup), чтобы свести две входные точки —
Instagram и TG-канал — к одному движку извлечения.
"""

from __future__ import annotations

import asyncio
import os
import traceback
import uuid
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from backend.config import INSTAGRAM_TEMP_DIR
from backend.services.instagram_reader import (
    cleanup_temp_files,
    extract_movies,
)
from backend.services.movie_resolver import resolve_movies


async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Извлекает фильмы из пересланного сообщения и предлагает добавить их."""
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
        if photo_sizes:
            # Берём фотку максимального разрешения — последняя в массиве.
            tg_file = await photo_sizes[-1].get_file()
            photo_path = Path(INSTAGRAM_TEMP_DIR) / f"forward_{uuid.uuid4().hex}.jpg"
            await tg_file.download_to_drive(custom_path=str(photo_path))
            frame_paths.append(str(photo_path))

        use_vision = bool(frame_paths)

        loop = asyncio.get_event_loop()
        movies_info = await loop.run_in_executor(
            None,
            extract_movies,
            "",
            text,
            frame_paths if frame_paths else None,
            use_vision,
        )

        if not movies_info:
            await status_msg.edit_text(
                "Не нашёл упоминаний фильмов в этом посте."
            )
            return

        await status_msg.edit_text(
            f"Нашёл {len(movies_info)} фильм(ов). Ищу в OMDB..."
        )

        resolved, unmatched = await resolve_movies(movies_info, log_tag="forward")

        for movie in resolved:
            await _send_movie_card(msg, movie)

        if unmatched:
            unmatched_list = ", ".join(f"«{t}»" for t in unmatched)
            await msg.reply_text(
                f"Не получилось найти в OMDB: {unmatched_list}"
            )

        if resolved:
            await status_msg.edit_text(
                f"Готово! Нашёл {len(resolved)} фильм(ов). "
                "Нажми «Добавить» под нужными."
            )
        else:
            await status_msg.edit_text(
                "Фильмы упоминаются, но не нашлись в OMDB."
            )

    except Exception as exc:
        print(f"[forward_handler] ERROR: {traceback.format_exc()}", flush=True)
        error_text = f"Ошибка: {type(exc).__name__}: {exc}"
        await status_msg.edit_text(error_text[:4000])
    finally:
        if frame_paths:
            cleanup_temp_files(frame_paths)


async def _send_movie_card(reply_to, movie) -> None:
    """Карточка фильма с кнопкой «Добавить» — повторяет формат из instagram_handler."""
    lines = [f"*{movie.title}* ({movie.year})"]
    if movie.description:
        lines.append(f"_{movie.description}_")
    text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Добавить в список",
            callback_data=f"add:{movie.imdb_id}",
        )]
    ])

    if movie.poster_url:
        try:
            await reply_to.reply_photo(
                photo=movie.poster_url,
                caption=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    await reply_to.reply_text(
        text, parse_mode="Markdown", reply_markup=keyboard,
    )
