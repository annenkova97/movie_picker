"""
Movie Picker — Telegram Bot
Запуск: python bot.py
"""

import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from backend.config import TELEGRAM_BOT_TOKEN
from backend.database import init_db
from handlers.start import start_command, help_command
from handlers.search import search_command
from handlers.add import add_command
from handlers.list import list_command, watched_command
from handlers.recommend import recommend_command, recommend_handler
from handlers.callbacks import callback_handler


async def post_init(application):
    """Инициализация БД при старте бота"""
    await init_db()
    print("База данных инициализирована.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не указан в .env")
        print("Получите токен у @BotFather в Telegram")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("watched", watched_command))
    app.add_handler(CommandHandler("recommend", recommend_command))

    # Callback-кнопки (add, watch, unwatch, delete)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Свободный текст → рекомендации
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        recommend_handler,
    ))

    print("Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()
