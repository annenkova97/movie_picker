from __future__ import annotations

import asyncio
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from backend.services.instagram_reader import (
    InstagramReaderError,
    validate_url,
    download_reel,
    extract_audio,
    transcribe,
    extract_movies,
    cleanup_temp_files,
)
from backend.services.omdb import omdb_service
from backend.services.llm import llm_service

REEL_URL_RE = re.compile(
    r"https?://(www\.)?instagram\.com/(reel|reels)/[\w-]+/?",
)


async def instagram_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка Instagram Reel ссылок — извлечение фильмов и поиск в OMDB."""
    text = update.message.text.strip()
    match = REEL_URL_RE.search(text)
    if not match:
        return

    url = match.group(0)

    try:
        validate_url(url)
    except InstagramReaderError:
        await update.message.reply_text(
            "Не удалось распознать ссылку на Instagram Reel."
        )
        return

    status_msg = await update.message.reply_text(
        "Обрабатываю Reel... Это может занять до минуты."
    )

    audio_path = None
    frame_paths: list[str] = []

    try:
        loop = asyncio.get_event_loop()

        video_path, caption = await loop.run_in_executor(None, download_reel, url)
        audio_path = await loop.run_in_executor(None, extract_audio, video_path)
        transcript = await loop.run_in_executor(None, transcribe, audio_path)

        movies_info = await loop.run_in_executor(
            None, extract_movies, transcript, caption, None, False,
        )

        if not movies_info:
            await status_msg.edit_text(
                "Не удалось найти фильмы в этом Reel."
            )
            return

        await status_msg.edit_text(
            f"Найдено {len(movies_info)} фильм(ов). Ищу в OMDB..."
        )

        found_any = False
        for item in movies_info:
            results = await _search_omdb(item.title_en, item.title_ru)

            if results:
                found_any = True
                r = results[0]

                # Подтягиваем полные данные и генерируем описание
                movie_base = await omdb_service.get_movie_by_id(r.imdb_id)
                description = ""
                if movie_base and movie_base.plot:
                    try:
                        description = await llm_service.generate_short_description(
                            movie_base.plot, movie_base.title,
                        )
                    except Exception:
                        pass

                lines = [f"*{r.title}* ({r.year})"]
                if description:
                    lines.append(f"_{description}_")
                if item.quote:
                    lines.append(f"\n\"{item.quote}\"")
                text = "\n".join(lines)

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "Добавить в список",
                        callback_data=f"add:{r.imdb_id}",
                    )]
                ])
                if r.poster_url:
                    try:
                        await update.message.reply_photo(
                            photo=r.poster_url,
                            caption=text,
                            parse_mode="Markdown",
                            reply_markup=keyboard,
                        )
                        continue
                    except Exception:
                        pass
                await update.message.reply_text(
                    text, parse_mode="Markdown", reply_markup=keyboard,
                )
            else:
                title = item.title_ru or item.title_en
                desc = f"\n_{item.description}_" if item.description else ""
                await update.message.reply_text(
                    f"*{title}* — не найден в OMDB{desc}",
                    parse_mode="Markdown",
                )

        if found_any:
            await status_msg.edit_text("Готово! Нажми «Добавить» под нужными фильмами.")
        else:
            await status_msg.edit_text("Фильмы из Reel не найдены в OMDB.")

    except InstagramReaderError as exc:
        await status_msg.edit_text(f"Ошибка: {exc}")
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[instagram_handler] ERROR: {tb}", flush=True)
        error_text = f"Ошибка: {type(exc).__name__}: {exc}"
        await status_msg.edit_text(error_text[:4000])
    finally:
        cleanup_targets = []
        if audio_path:
            cleanup_targets.append(audio_path)
        if frame_paths:
            cleanup_targets.extend(frame_paths)
        cleanup_temp_files(cleanup_targets)


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
