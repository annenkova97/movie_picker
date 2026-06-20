import asyncio

from telegram import Update
from telegram.ext import ContextTypes


# Per design §6.6: four short bubble messages introducing the value, then a
# final prompt that tells the user how to start. Illustrations (the in-design
# inline mini-art) are still TODO — generated PNGs will land in
# handlers/assets/onboarding/ and be attached as photos with these as captions.
_ONBOARDING_BUBBLES = (
    "Привет, я Ленточка. Сохраняй фильмы откуда угодно — "
    "Instagram, Telegram, от друзей.",
    "Всё собирается в одном месте — с источниками, чтобы помнить, "
    "от кого что.",
    "Подберу под настроение на вечер — напиши, чего хочется, "
    "или открой Mini-App.",
    "Смотри вдвоём — без отдельных аккаунтов, общий список с кем-то близким.",
)

_ONBOARDING_FINAL = "Готова? Форвардни любой фильм 👇"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Onboarding в голосе бренда — 4 короткие реплики + финальный prompt."""
    # app_open из бота: резолвим юзера (как и при добавлении) для retention.
    try:
        from handlers.analytics import track_bot
        from handlers.callbacks import _get_or_create_user
        user_row = await _get_or_create_user(update.effective_user)
        await track_bot("app_open", user_row["id"], {"via": "start"})
    except Exception:
        pass

    for bubble in _ONBOARDING_BUBBLES:
        await update.message.reply_text(bubble)
        # Tiny pause so the bubbles arrive one-by-one, не сваливаются стопкой.
        await asyncio.sleep(0.4)
    await update.message.reply_text(_ONBOARDING_FINAL)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Краткий референс команд — для тех, кто хочет CLI-режим."""
    text = (
        "Что умею:\n\n"
        "/add <название> — сохранить фильм по названию или IMDb-id\n"
        "/search <название> — найти в базе, посмотреть карточку\n"
        "/list — твой список\n"
        "/watched — просмотренные\n"
        "/recommend <запрос> — подберу из списка под настроение\n\n"
        "Ещё можно:\n"
        "• скинуть ссылку на Instagram Reel — разберу и предложу сохранить\n"
        "• просто написать «что-то лёгкое» — пойму как запрос на рекомендацию"
    )
    await update.message.reply_text(text)
