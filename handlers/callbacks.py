from telegram import Update
from telegram.ext import ContextTypes

from backend import database as db
from backend.services.omdb import omdb_service
from backend.services.llm import llm_service


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех callback-кнопок"""
    query = update.callback_query
    await query.answer()

    data = query.data
    action, value = data.split(":", 1)

    if action == "add":
        await _handle_add(query, value)
    elif action == "watch":
        await _handle_watch(query, int(value), watched=True)
    elif action == "unwatch":
        await _handle_watch(query, int(value), watched=False)
    elif action == "delete":
        await _handle_delete(query, int(value))


async def _handle_add(query, imdb_id: str):
    """Добавление фильма по IMDb ID"""
    # Проверяем дубликат
    existing = await db.get_movie_by_imdb_id(imdb_id)
    if existing:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"«{existing.title}» уже есть в списке."
        )
        return

    # Получаем данные из OMDB
    movie_base = await omdb_service.get_movie_by_id(imdb_id)
    if not movie_base:
        await query.message.reply_text("Не удалось загрузить данные фильма.")
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
    movie = await db.add_movie(movie_base, source="personal")

    # Убираем кнопку «Добавить»
    await query.edit_message_reply_markup(reply_markup=None)

    rating = f" | IMDb {movie.imdb_rating}" if movie.imdb_rating else ""
    await query.message.reply_text(
        f"Добавлен: *{movie.title}* ({movie.year}){rating}",
        parse_mode="Markdown",
    )


async def _handle_watch(query, movie_id: int, watched: bool):
    """Отметить фильм просмотренным/непросмотренным"""
    movie = await db.update_movie(movie_id, is_watched=watched)
    if not movie:
        await query.message.reply_text("Фильм не найден.")
        return

    status = "просмотрен ✅" if watched else "возвращён в список 🎬"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"*{movie.title}* — {status}", parse_mode="Markdown"
    )


async def _handle_delete(query, movie_id: int):
    """Удаление фильма"""
    movie = await db.get_movie_by_id(movie_id)
    title = movie.title if movie else "Фильм"

    success = await db.delete_movie(movie_id)
    if not success:
        await query.message.reply_text("Фильм не найден.")
        return

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"«{title}» удалён из списка.")
