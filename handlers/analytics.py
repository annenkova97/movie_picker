"""Лёгкий трекинг событий из бота — пишет в ту же таблицу ``events``.

Зеркало фронтового ``analytics.ts``, но source='bot'. Best-effort: любые
ошибки глушим, аналитика не должна ронять обработку Telegram-апдейта.
"""
from __future__ import annotations

from typing import Optional

from backend import database as db
from backend.models.event import ALLOWED_EVENTS


async def track_bot(
    name: str, user_id: Optional[int], props: Optional[dict] = None
) -> None:
    """Записать событие из бота. Имена — из общего allowlist (см. модель)."""
    if name not in ALLOWED_EVENTS:
        return
    try:
        await db.insert_events([{
            "name": name,
            "user_id": user_id,
            "props": props or {},
            "source": "bot",
        }])
    except Exception as exc:  # аналитика не ломает бота
        print(f"[analytics] bot track failed: {exc}")
