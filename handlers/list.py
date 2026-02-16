from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from backend import database as db


def _format_movie(movie) -> str:
    """Форматирование фильма для сообщения"""
    watched = "✅" if movie.is_watched else "🎬"
    rating = f" | IMDb {movie.imdb_rating}" if movie.imdb_rating else ""
    year = f" ({movie.year})" if movie.year else ""
    genres = f"\n{', '.join(movie.genres)}" if movie.genres else ""
    desc = f"\n_{movie.description}_" if movie.description else ""

    return f"{watched} *{movie.title}*{year}{rating}{genres}{desc}"


def _movie_keyboard(movie) -> InlineKeyboardMarkup:
    """Кнопки для фильма"""
    buttons = []

    if movie.is_watched:
        buttons.append(InlineKeyboardButton(
            "Отметить непросмотренным", callback_data=f"unwatch:{movie.id}"
        ))
    else:
        buttons.append(InlineKeyboardButton(
            "Просмотрено ✅", callback_data=f"watch:{movie.id}"
        ))

    buttons.append(InlineKeyboardButton(
        "Удалить ❌", callback_data=f"delete:{movie.id}"
    ))

    return InlineKeyboardMarkup([buttons])


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /list — непросмотренные фильмы"""
    movies = await db.get_all_movies(is_watched=False)

    if not movies:
        await update.message.reply_text(
            "Список пуст. Добавь фильмы через /search <название>"
        )
        return

    await update.message.reply_text(
        f"Фильмы к просмотру ({len(movies)}):"
    )

    # Показываем по 5 фильмов
    for movie in movies[:10]:
        text = _format_movie(movie)
        keyboard = _movie_keyboard(movie)
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )

    if len(movies) > 10:
        await update.message.reply_text(
            f"...и ещё {len(movies) - 10} фильмов"
        )


async def list_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок в списке — делегируется в callbacks"""
    pass


async def watched_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /watched — просмотренные фильмы"""
    movies = await db.get_all_movies(is_watched=True)

    if not movies:
        await update.message.reply_text("Нет просмотренных фильмов.")
        return

    await update.message.reply_text(
        f"Просмотренные фильмы ({len(movies)}):"
    )

    for movie in movies[:10]:
        text = _format_movie(movie)
        keyboard = _movie_keyboard(movie)
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )

    if len(movies) > 10:
        await update.message.reply_text(
            f"...и ещё {len(movies) - 10} фильмов"
        )
