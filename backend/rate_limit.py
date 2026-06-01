"""Rate limiting via slowapi.

Two key functions:
- ``client_ip_key`` — клиент по IP, для неавторизованных эндпоинтов (auth,
  публичный поиск). Уважает X-Forwarded-For, потому что Railway / любой PaaS
  сидит за прокси и ``request.client.host`` иначе всегда один и тот же.
- ``user_or_ip_key`` — для эндпоинтов с (опциональной) авторизацией: ключ по
  user_id из JWT, fallback на IP, если токена нет. Так гость и залогиненный
  юзер считаются раздельно, а лимит на платные API не обходится разлогином.

Лимитер можно выключить переменной окружения ``RATE_LIMIT_ENABLED=0`` — это
используется в тестах, чтобы обычные кейсы не упирались в лимит (а отдельный
тест включает лимитер обратно и проверяет, что 429 действительно прилетает).
"""
from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter

from backend.auth import decode_access_token


def client_ip_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def user_or_ip_key(request: Request) -> str:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1].strip()
        user_id = decode_access_token(token)
        if user_id is not None:
            return f"user:{user_id}"
    return f"ip:{client_ip_key(request)}"


_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1").strip().lower() not in {"0", "false", "no"}

limiter = Limiter(key_func=client_ip_key, enabled=_ENABLED)
