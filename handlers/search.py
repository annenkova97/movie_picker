from telegram import Message, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from backend.models.movie import OMDBSearchResult
from backend.services.title_search import search_title


async def send_search_results(
    message: Message, results: list[OMDBSearchResult]
) -> None:
    """Отправляет до 5 карточек результатов поиска с кнопкой «+ Сохранить».

    Общий помощник: используется и в /search, и в свободном текстовом поиске
    (handlers.recommend.text_handler). Рендерит в переданный ``message``.
    """
    for item in results[:5]:
        text = f"*{item.title}* ({item.year})"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "+ Сохранить",
                callback_data=f"add:{item.imdb_id}"
            )]
        ])

        if item.poster_url:
            try:
                await message.reply_photo(
                    photo=item.poster_url,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
                continue
            except Exception:
                pass

        await message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard,
        )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /search <название>"""
    if not context.args:
        await update.message.reply_text(
            "Укажи название фильма после команды.\n"
            "Пример: /search Inception"
        )
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"Ищу «{query}»...")

    results = await search_title(query)

    if not results:
        await update.message.reply_text(
            f"По «{query}» ничего не нашла. "
            "Попробуй другое название (лучше на английском)."
        )
        return

    await send_search_results(update.message, results)
