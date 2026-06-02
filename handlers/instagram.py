from __future__ import annotations

import asyncio
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from backend.services.instagram_reader import (
    InstagramReaderError,
    validate_url,
    download_reel,
    extract_movies,
    cleanup_temp_files,
)
from backend.services.omdb import omdb_service
from backend.services.llm import llm_service
from handlers.formatting import format_imdb_rating

REEL_URL_RE = re.compile(
    r"https?://(www\.)?instagram\.com/(reel|reels)/[\w-]+/?",
)


async def instagram_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка Instagram Reel ссылок — извлечение фильмов и поиск в OMDB.

    Voice: friendly butler, first-person feminine ("разбираю", "нашла",
    "сохранить можно..."). Caption layout follows design §6.3 Save
    Confirmation: title + meta · italic rationale · source attribution.
    """
    text = update.message.text.strip()
    match = REEL_URL_RE.search(text)
    if not match:
        return

    url = match.group(0)

    try:
        validate_url(url)
    except InstagramReaderError:
        await update.message.reply_text(
            "Не разобрала ссылку. Это точно Reel?"
        )
        return

    status_msg = await update.message.reply_text(
        "Разбираю Reel — это до минуты."
    )

    frame_paths: list[str] = []

    try:
        loop = asyncio.get_event_loop()

        # Apify даёт сразу caption + transcript; видео нам в боте не нужно
        # (vision-режим не используется).
        _video_path, caption, transcript = await loop.run_in_executor(
            None, download_reel, url,
        )

        movies_info = await loop.run_in_executor(
            None, extract_movies, transcript, caption, None, False,
        )

        if not movies_info:
            await status_msg.edit_text(
                "В этом Reel не нашла фильмов."
            )
            return

        await status_msg.edit_text(
            f"Нашла {_films_pluralize(len(movies_info))}. Подтягиваю детали..."
        )

        found_any = False
        for item in movies_info:
            results = await _search_omdb(item.title_en, item.title_ru)

            if results:
                found_any = True
                r = results[0]

                # Подтягиваем полные данные и генерируем описание.
                movie_base = await omdb_service.get_movie_by_id(r.imdb_id)
                description = ""
                if movie_base and movie_base.plot:
                    try:
                        description = await llm_service.generate_short_description(
                            movie_base.plot, movie_base.title,
                        )
                    except Exception:
                        pass

                caption_text = _format_film_caption(
                    title=r.title,
                    year=r.year,
                    imdb_rating=getattr(movie_base, "imdb_rating", None) if movie_base else None,
                    quote=item.quote,
                    description=description,
                    reel_url=url,
                )

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "+ Сохранить",
                        callback_data=f"add:{r.imdb_id}",
                    )]
                ])
                if r.poster_url:
                    try:
                        await update.message.reply_photo(
                            photo=r.poster_url,
                            caption=caption_text,
                            parse_mode="Markdown",
                            reply_markup=keyboard,
                        )
                        continue
                    except Exception:
                        pass
                await update.message.reply_text(
                    caption_text, parse_mode="Markdown", reply_markup=keyboard,
                )
            else:
                title = item.title_ru or item.title_en
                desc = f"\n_{item.description}_" if item.description else ""
                await update.message.reply_text(
                    f"*{title}* — не нашла в базе{desc}",
                    parse_mode="Markdown",
                )

        if found_any:
            await status_msg.edit_text("Готово. Сохранить можно под каждым 👇")
        else:
            await status_msg.edit_text("Фильмы из Reel не нашлись в базе.")

    except InstagramReaderError as exc:
        await status_msg.edit_text(f"Не получилось: {exc}")
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[instagram_handler] ERROR: {tb}", flush=True)
        error_text = f"Не получилось: {type(exc).__name__}: {exc}"
        await status_msg.edit_text(error_text[:4000])
    finally:
        if frame_paths:
            cleanup_temp_files(frame_paths)


def _films_pluralize(n: int) -> str:
    """Russian plural: 1 фильм, 2-4 фильма, 5+ фильмов."""
    last_two = n % 100
    last = n % 10
    if 11 <= last_two <= 14:
        return f"{n} фильмов"
    if last == 1:
        return f"{n} фильм"
    if 2 <= last <= 4:
        return f"{n} фильма"
    return f"{n} фильмов"


def _format_film_caption(
    *,
    title: str,
    year,
    imdb_rating,
    quote: str | None,
    description: str,
    reel_url: str,
) -> str:
    """Build the Save Confirmation caption per design §6.3.

    Layout (legacy Markdown):

        *Title* (Year)
        ★ 7.6

        _«italic-rationale»_

        📷 из [Instagram](url)

    `quote` (from the Reel transcript) takes priority over the LLM-generated
    `description` because a source quote preserves the original recommendation's
    emotional energy. Either is wrapped in Russian guillemets «».
    """
    header = f"*{title}*" + (f" ({year})" if year else "")
    meta_parts: list[str] = []
    if imdb_rating:
        meta_parts.append(f"★ {format_imdb_rating(imdb_rating)}")
    meta = " · ".join(meta_parts)

    if quote:
        italic = f"_«{quote.strip().strip(chr(34))}»_"
    elif description:
        italic = f"_«{description.strip()}»_"
    else:
        italic = ""

    source = f"📷 из [Instagram]({reel_url})"

    parts = [header]
    if meta:
        parts.append(meta)
    if italic:
        parts.append("")
        parts.append(italic)
    parts.append("")
    parts.append(source)
    return "\n".join(parts)


async def _search_omdb(
    title_en: str, title_ru: str,
) -> list:
    """Поиск в OMDB с фолбэком по нескольким стратегиям."""
    for query in [title_en, title_ru]:
        if not query:
            continue
        results = await omdb_service.search_movies(query)
        if results:
            return results

    for query in [title_en, title_ru]:
        if not query:
            continue
        results = await omdb_service.search_movies(query, media_type="")
        if results:
            return results

    return []
