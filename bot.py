"""
Movie Picker — Telegram Bot (локальная разработка, long-polling)
Запуск: python bot.py

Прод использует webhook (см. backend.main lifespan). Регистрация хендлеров —
общая, в bot_setup.register_handlers, чтобы оба транспорта не разъезжались.
"""

from backend.config import TELEGRAM_BOT_TOKEN
from backend.database import init_db
from bot_setup import build_application


async def post_init(application):
    """Инициализация БД при старте бота."""
    await init_db()
    print("База данных инициализирована.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не указан в .env")
        print("Получите токен у @BotFather в Telegram")
        return

    app = build_application(post_init=post_init)

    print("Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
