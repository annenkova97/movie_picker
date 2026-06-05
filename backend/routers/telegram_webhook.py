"""Telegram webhook endpoint — feeds updates into the in-process PTB Application.

The bot runs inside the web process in production (see ``backend.main``
lifespan): Telegram POSTs updates to ``/telegram/webhook/<secret>`` and we hand
them to ``Application.process_update``. The secret path segment keeps random
callers from injecting fake updates.

When the bot isn't configured (no token / base URL), ``app.state.bot_app`` is
None and this route returns 503 — harmless and inert.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from telegram import Update

from backend.config import TELEGRAM_WEBHOOK_SECRET

router = APIRouter(prefix="/telegram", tags=["telegram-webhook"])


@router.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if not TELEGRAM_WEBHOOK_SECRET or secret != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="bad webhook secret")

    bot_app = getattr(request.app.state, "bot_app", None)
    if bot_app is None:
        raise HTTPException(status_code=503, detail="bot not running")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}
