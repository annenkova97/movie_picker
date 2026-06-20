"""Событийная аналитика: приём батчей событий от фронта.

``POST /api/events`` — фронт буферизует события и шлёт пачкой. Сервер ставит
``user_id`` (из токена, если есть), ``source='web'`` и собственный ts. Имена
вне allowlist отбрасываются. Аналитика best-effort: сбой записи не должен
ломать клиента, поэтому ошибки глушим и всё равно отвечаем 200.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Request

from backend import database as db
from backend.auth import get_current_user_optional
from backend.models import EventBatch, User
from backend.models.event import ALLOWED_EVENTS, MAX_PROPS_KEYS
from backend.rate_limit import limiter, user_or_ip_key

router = APIRouter(prefix="/api/events", tags=["analytics"])


@router.post("")
@limiter.limit("600/hour", key_func=user_or_ip_key)
async def post_events(
    request: Request,
    payload: EventBatch,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    user_id = current_user.id if current_user else None
    rows: list[dict] = []
    for event in payload.events:
        if event.name not in ALLOWED_EVENTS:
            continue  # мусор/неизвестные имена молча отбрасываем
        props = event.props if isinstance(event.props, dict) else {}
        if len(props) > MAX_PROPS_KEYS:
            props = dict(list(props.items())[:MAX_PROPS_KEYS])
        rows.append({
            "user_id": user_id,
            "anon_id": event.anon_id,
            "name": event.name,
            "props": props,
            "source": "web",
        })

    if rows:
        try:
            await db.insert_events(rows)
        except Exception as exc:  # аналитика не роняет клиента
            print(f"[events] insert failed: {exc}")

    return {"accepted": len(rows)}
