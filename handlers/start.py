from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    text = (
        "Привет! Я помогу управлять твоим списком фильмов.\n\n"
        "Вот что я умею:\n"
        "/add <название> — добавить фильм в список\n"
        "/search <название> — найти фильм в OMDB\n"
        "/list — показать мой список\n"
        "/watched — показать просмотренные\n"
        "/recommend <запрос> — получить рекомендацию из списка\n"
        "/help — справка\n\n"
        "Можно и без команд:\n"
        "• напиши название фильма — я найду его в OMDB и предложу похожие;\n"
        "• пришли ссылку на Instagram Reel — вытащу упомянутые фильмы;\n"
        "• перешли пост из ТГ-канала (с текстом или фото фильма) — "
        "разберу и предложу добавить;\n"
        "• свободный запрос вроде «что-то лёгкое» — подберу из твоего списка."
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /help"""
    text = (
        "Команды:\n\n"
        "/add <название> — добавить фильм в список\n"
        "  Пример: /add Inception\n"
        "  Пример: /add tt0468569\n\n"
        "/search <название> — поиск фильма по названию\n"
        "  Пример: /search Inception\n\n"
        "/list — все фильмы к просмотру\n"
        "/watched — просмотренные фильмы\n\n"
        "/recommend <запрос> — AI-рекомендация из твоего списка\n"
        "  Примеры:\n"
        "  /recommend что-то лёгкое\n"
        "  /recommend драма с Ди Каприо\n"
        "  /recommend триллер, но не страшный\n\n"
        "Без команд тоже работает:\n"
        "• «Inception» / «Бойцовский клуб» — найду в OMDB;\n"
        "• Instagram Reel — пришли ссылку, вытащу фильмы;\n"
        "• Пересланный пост из ТГ-канала с описанием или фото фильма — "
        "разберу и предложу добавить;\n"
        "• «что-то лёгкое и смешное» — подберу из твоего списка."
    )
    await update.message.reply_text(text)
