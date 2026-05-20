from telegram import Update
from telegram.ext import ContextTypes

from backend import database as db
from backend.services.omdb import omdb_service
from backend.services.llm import llm_service
from handlers.callbacks import _get_or_create_user


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/add <название или IMDb ID> — добавить фильм в список"""
    if not context.args:
        await update.message.reply_text(
            "Укажи название фильма или IMDb ID.\n"
            "Примеры:\n"
            "  /add Inception\n"
            "  /add tt0468569"
        )
        return

    query = " ".join(context.args).strip()
    await update.message.reply_text(f"Ищу «{query}»...")

    # Определяем: IMDb ID или название
    if query.startswith("tt") and query[2:].isdigit():
        movie_base = await omdb_service.get_movie_by_id(query)
    else:
        movie_base = await omdb_service.get_movie_by_title(query)

    if not movie_base:
        await update.message.reply_text(
            f"Не нашла «{query}» в базе. "
            "Попробуй на английском или /search."
        )
        return

    user_row = await _get_or_create_user(update.effective_user)
    user_id = user_row["id"]

    # Проверяем дубликат
    existing = await db.get_user_movie_by_imdb_id(movie_base.imdb_id, user_id)
    if existing:
        await update.message.reply_text(
            f"«{existing.title}» уже в твоём списке."
        )
        return

    # Генерируем описание
    if movie_base.plot:
        try:
            description = await llm_service.generate_short_description(
                movie_base.plot, movie_base.title
            )
            movie_base.description = description
        except Exception:
            pass

    # Сохраняем
    movie = await db.add_movie(movie_base, user_id=user_id, source="telegram")

    rating = f"  ★ {movie.imdb_rating}" if movie.imdb_rating else ""
    year = f" ({movie.year})" if movie.year else ""
    genres = f"\n{', '.join(movie.genres)}" if movie.genres else ""
    desc = f"\n_«{movie.description}»_" if movie.description else ""

    await update.message.reply_text(
        f"Сохранила: *{movie.title}*{year}{rating}{genres}{desc}",
        parse_mode="Markdown",
    )
