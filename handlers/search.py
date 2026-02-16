from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from backend.services.omdb import omdb_service


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

    results = await omdb_service.search_movies(query)

    if not results:
        await update.message.reply_text(
            f"По запросу «{query}» ничего не найдено. "
            "Попробуй другое название (лучше на английском)."
        )
        return

    # Показываем до 5 результатов с кнопками «Добавить»
    for item in results[:5]:
        text = f"*{item.title}* ({item.year})"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "Добавить в список",
                callback_data=f"add:{item.imdb_id}"
            )]
        ])

        if item.poster_url:
            try:
                await update.message.reply_photo(
                    photo=item.poster_url,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
                continue
            except Exception:
                pass

        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )


async def search_inline_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Добавить' из поиска — делегируется в callbacks"""
    pass
