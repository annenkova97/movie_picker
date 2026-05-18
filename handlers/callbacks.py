from telegram import Update
from telegram.ext import ContextTypes

from backend import database as db
from backend.services.omdb import omdb_service
from backend.services.llm import llm_service


async def _get_or_create_user(tg_user) -> dict:
    """Находит или создаёт юзера в БД по telegram_id из callback'а.

    Telegram не отдаёт email, поэтому выдаём синтетический ``tg<id>@telegram.local``.
    Тот же подход используется в /auth/telegram-webapp на фронте — поэтому
    юзер, добавивший фильмы в боте, видит их же при открытии Mini App.
    """
    telegram_id = int(tg_user.id)
    row = await db.get_user_by_telegram_id(telegram_id)
    if row:
        return row

    name_parts = [tg_user.first_name or "", tg_user.last_name or ""]
    full_name = " ".join(p for p in name_parts if p).strip() or (tg_user.username or "")
    return await db.create_user(
        # Synthetic email — example.com зарезервирован RFC 2606.
        email=f"tg{telegram_id}@tg.example.com",
        telegram_id=telegram_id,
        name=full_name or None,
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех callback-кнопок"""
    query = update.callback_query
    await query.answer()

    user_row = await _get_or_create_user(query.from_user)
    user_id = user_row["id"]

    data = query.data
    action, value = data.split(":", 1)

    if action == "add":
        await _handle_add(query, value, user_id=user_id)
    elif action == "watch":
        await _handle_watch(query, int(value), user_id=user_id, watched=True)
    elif action == "unwatch":
        await _handle_watch(query, int(value), user_id=user_id, watched=False)
    elif action == "delete":
        await _handle_delete(query, int(value), user_id=user_id)


async def _handle_add(query, imdb_id: str, *, user_id: int):
    """Добавление фильма по IMDb ID в библиотеку конкретного юзера."""
    existing = await db.get_user_movie_by_imdb_id(imdb_id, user_id)
    if existing:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"«{existing.title}» уже есть в твоём списке."
        )
        return

    movie_base = await omdb_service.get_movie_by_id(imdb_id)
    if not movie_base:
        await query.message.reply_text("Не удалось загрузить данные фильма.")
        return

    if movie_base.plot:
        try:
            description = await llm_service.generate_short_description(
                movie_base.plot, movie_base.title
            )
            movie_base.description = description
        except Exception:
            pass

    movie = await db.add_movie(movie_base, user_id=user_id, source="telegram")

    await query.edit_message_reply_markup(reply_markup=None)

    rating = f" | IMDb {movie.imdb_rating}" if movie.imdb_rating else ""
    await query.message.reply_text(
        f"Добавлен: *{movie.title}* ({movie.year}){rating}",
        parse_mode="Markdown",
    )


async def _handle_watch(query, movie_id: int, *, user_id: int, watched: bool):
    """Отметить фильм просмотренным/непросмотренным."""
    movie = await db.update_movie(movie_id, user_id=user_id, is_watched=watched)
    if not movie:
        await query.message.reply_text("Фильм не найден.")
        return

    status = "просмотрен ✅" if watched else "возвращён в список 🎬"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"*{movie.title}* — {status}", parse_mode="Markdown"
    )


async def _handle_delete(query, movie_id: int, *, user_id: int):
    """Удаление фильма из библиотеки юзера."""
    movie = await db.get_movie_by_id(movie_id, user_id=user_id)
    title = movie.title if movie else "Фильм"

    success = await db.delete_movie(movie_id, user_id=user_id)
    if not success:
        await query.message.reply_text("Фильм не найден.")
        return

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"«{title}» удалён из списка.")
