"""Shared Telegram-bot wiring — one place that registers all handlers.

Used by both entry points so they never drift:
  - ``bot.py``            — local dev, long-polling.
  - ``backend.main``      — production, webhook fed from a FastAPI route.

Keeping registration here (instead of duplicated in each) is the DRY win: add a
handler once and both transports get it.
"""

from __future__ import annotations

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from backend.config import TELEGRAM_BOT_TOKEN
from handlers.start import start_command, help_command
from handlers.search import search_command
from handlers.add import add_command
from handlers.list import list_command, watched_command
from handlers.recommend import recommend_command, text_handler
from handlers.callbacks import callback_handler, note_reply_handler
from handlers.instagram import instagram_handler
from handlers.forward import forward_handler


def register_handlers(app: Application) -> None:
    """Attach every command/message/callback handler to ``app``."""
    # Note-reply interceptor lives in an earlier group so it can grab the
    # "add a note" reply before the generic text handler sees it.
    app.add_handler(
        MessageHandler(
            filters.REPLY & filters.TEXT & ~filters.COMMAND,
            note_reply_handler,
        ),
        group=-1,
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("watched", watched_command))
    app.add_handler(CommandHandler("recommend", recommend_command))

    app.add_handler(CallbackQueryHandler(callback_handler))

    # Instagram Reels (ловим раньше FORWARDED — пересланный Reel тоже сюда).
    app.add_handler(MessageHandler(
        filters.Regex(r"https?://(www\.)?instagram\.com/(reel|reels)/"),
        instagram_handler,
    ))

    # Пересланные посты из TG-каналов: текст или фото → фильмы и книги.
    app.add_handler(MessageHandler(
        filters.FORWARDED & (filters.TEXT | filters.PHOTO | filters.CAPTION),
        forward_handler,
    ))

    # Свободный текст → поиск/рекомендация. Пересланные уже отработаны выше.
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.FORWARDED,
        text_handler,
    ))


def build_application(post_init=None) -> Application:
    """Build a PTB Application with all handlers registered.

    ``concurrent_updates(True)`` lets the long-polling path (``bot.py``) process
    updates in parallel instead of one-at-a-time, so a slow handler no longer
    blocks every other tap. The webhook path feeds ``process_update`` directly
    per HTTP request, so it's already concurrent there — the flag is harmless.
    """
    builder = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True)
    if post_init is not None:
        builder = builder.post_init(post_init)
    app = builder.build()
    register_handlers(app)
    return app
