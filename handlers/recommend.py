from telegram import Update
from telegram.ext import ContextTypes

from backend import database as db
from backend.services.llm import llm_service
from backend.services.title_search import search_title
from handlers.formatting import imdb_suffix
from handlers.search import send_search_results


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /recommend <запрос> — рекомендация из библиотеки."""
    if not context.args:
        await update.message.reply_text(
            "Напиши, что хочется посмотреть.\n"
            "Например: /recommend что-то лёгкое и смешное"
        )
        return

    query = " ".join(context.args)
    await _do_recommend(update, query)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Свободный текст: пост → экстрактор, название → поиск, иначе рекомендация.

    Три сценария одной строкой:
    - длинный/многострочный текст (вставленный пост) → извлекаем все фильмы
      и книги разом (handlers.forward);
    - «Inception» / «Бойцовский клуб» → карточки фильмов с кнопкой «Добавить»;
    - «что-то лёгкое и смешное» → AI-подбор из списка пользователя.
    """
    query = update.message.text.strip()
    if not query:
        return

    # Вставленный пост (несколько строк / длинный абзац) — не название и не
    # запрос: гоним через общий экстрактор фильмов и книг.
    from handlers.forward import looks_like_post, process_pasted_text
    if looks_like_post(query):
        await process_pasted_text(update, context)
        return

    results = await search_title(query)
    if results:
        await update.message.reply_text(
            f"Похоже на название фильма «{query}». Вот ближайшие совпадения:"
        )
        await send_search_results(update.message, results[:5])
        return

    await _do_recommend(update, query)


async def _do_recommend(update: Update, query: str):
    """Общая логика рекомендаций"""
    movies = await db.get_unwatched_movies()

    if not movies:
        await update.message.reply_text(
            "В списке пока нет непросмотренных. "
            "Добавь через /search или скинь Reel."
        )
        return

    await update.message.reply_text(f"Подбираю под «{query}»...")

    try:
        recommended_ids, explanation = await llm_service.recommend_movies(
            query, movies, max_recommendations=3
        )
    except Exception as e:
        print(f"Ошибка рекомендаций: {type(e).__name__}: {e}")
        await update.message.reply_text(
            f"Не получилось: {type(e).__name__}: {e}"
        )
        return

    if not recommended_ids:
        await update.message.reply_text(
            f"Под «{query}» ничего не нашла в твоём списке.\n\n"
            f"{explanation}"
        )
        return

    # Находим рекомендованные фильмы
    recommended = [m for m in movies if m.id in recommended_ids]
    id_to_order = {id_: idx for idx, id_ in enumerate(recommended_ids)}
    recommended.sort(key=lambda m: id_to_order.get(m.id, 999))

    # Отправляем результат
    text = f"Под «{query}»:\n\n"

    for i, movie in enumerate(recommended, 1):
        rating = imdb_suffix(movie.imdb_rating, "  ★ ")
        year = f" ({movie.year})" if movie.year else ""
        genres = f" — {', '.join(movie.genres)}" if movie.genres else ""
        text += f"{i}. *{movie.title}*{year}{rating}{genres}\n"
        if movie.description:
            text += f"   _«{movie.description}»_\n"
        text += "\n"

    text += f"💡 {explanation}"

    await update.message.reply_text(text, parse_mode="Markdown")
