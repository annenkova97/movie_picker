from telegram import Update
from telegram.ext import ContextTypes

from backend import database as db
from backend.services.llm import llm_service


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /recommend <запрос>"""
    if not context.args:
        await update.message.reply_text(
            "Напиши, что хочешь посмотреть.\n"
            "Пример: /recommend что-то лёгкое и смешное"
        )
        return

    query = " ".join(context.args)
    await _do_recommend(update, query)


async def recommend_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка свободного текста как запроса на рекомендацию"""
    query = update.message.text.strip()
    if not query:
        return
    await _do_recommend(update, query)


async def _do_recommend(update: Update, query: str):
    """Общая логика рекомендаций"""
    movies = await db.get_unwatched_movies()

    if not movies:
        await update.message.reply_text(
            "В списке пока нет непросмотренных фильмов. "
            "Добавь фильмы через /search <название>"
        )
        return

    await update.message.reply_text(f"Подбираю фильмы по запросу «{query}»...")

    try:
        recommended_ids, explanation = await llm_service.recommend_movies(
            query, movies, max_recommendations=3
        )
    except Exception as e:
        print(f"Ошибка рекомендаций: {type(e).__name__}: {e}")
        await update.message.reply_text(
            f"Ошибка: {type(e).__name__}: {e}"
        )
        return

    if not recommended_ids:
        await update.message.reply_text(
            f"По запросу «{query}» ничего не нашлось в твоём списке.\n\n"
            f"{explanation}"
        )
        return

    # Находим рекомендованные фильмы
    recommended = [m for m in movies if m.id in recommended_ids]
    id_to_order = {id_: idx for idx, id_ in enumerate(recommended_ids)}
    recommended.sort(key=lambda m: id_to_order.get(m.id, 999))

    # Отправляем результат
    text = f"По запросу «{query}» рекомендую:\n\n"

    for i, movie in enumerate(recommended, 1):
        rating = f" | IMDb {movie.imdb_rating}" if movie.imdb_rating else ""
        year = f" ({movie.year})" if movie.year else ""
        genres = f" — {', '.join(movie.genres)}" if movie.genres else ""
        text += f"{i}. *{movie.title}*{year}{rating}{genres}\n"
        if movie.description:
            text += f"   _{movie.description}_\n"
        text += "\n"

    text += f"💡 {explanation}"

    await update.message.reply_text(text, parse_mode="Markdown")
