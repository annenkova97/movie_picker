"""Аутентификация: хэш паролей, JWT, проверка Google ID-токена и Telegram WebApp initData."""
from __future__ import annotations

import bcrypt
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qsl

import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from backend import database as db
from backend.config import (
    JWT_SECRET,
    JWT_EXPIRES_DAYS,
    JWT_ALGORITHM,
    GOOGLE_CLIENT_ID,
    TELEGRAM_BOT_TOKEN,
)
from backend.models import User


# initData считается «свежим» 24 часа — достаточно, чтобы пережить
# короткую офлайн-сессию, но мало для серьёзного replay-attack.
TELEGRAM_INITDATA_MAX_AGE_SECONDS = 24 * 60 * 60


_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=JWT_EXPIRES_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def verify_google_id_token(token: str) -> dict:
    """Проверяет подпись Google ID-токена и возвращает claims.

    Бросает HTTPException 401 при любой ошибке проверки.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google вход не настроен (GOOGLE_CLIENT_ID не задан на сервере)",
        )
    try:
        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Некорректный Google-токен: {exc}",
        )
    if not claims.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email в Google-аккаунте не подтверждён",
        )
    return claims


def verify_telegram_init_data(init_data: str) -> dict:
    """Проверяет подпись Telegram Mini App initData и возвращает payload.

    Алгоритм по `docs.telegram.org/bots/webapps#validating-data-received-via-the-mini-app`:
      1. Распарсить initData как querystring.
      2. Извлечь `hash`, остальные пары отсортировать по ключу.
      3. ``data_check_string = "\n".join(f"{k}={v}")``.
      4. ``secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)``.
      5. Сравнить ``HMAC_SHA256(secret_key, data_check_string)`` с ``hash``.

    Дополнительно проверяем ``auth_date``, чтобы старые initData нельзя было
    переиспользовать (replay).

    Бросает HTTPException 401 при любой ошибке. На успех возвращает словарь
    распарсенных полей с user-объектом в ``"user"``.
    """
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Telegram вход не настроен (TELEGRAM_BOT_TOKEN не задан)",
        )
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пустой initData",
        )

    # parse_qsl сам сделает URL-decode для значений (включая `user` с %7B и т.п.)
    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    data = dict(pairs)
    received_hash = data.pop("hash", "")
    if not received_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData без поля hash",
        )

    data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret_key = hmac.new(
        b"WebAppData", TELEGRAM_BOT_TOKEN.encode("utf-8"), hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная подпись initData",
        )

    try:
        auth_date = int(data.get("auth_date", "0"))
    except ValueError:
        auth_date = 0
    if auth_date and (time.time() - auth_date) > TELEGRAM_INITDATA_MAX_AGE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData устарел, перезайди в приложение",
        )

    user_field = data.get("user")
    if not user_field:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData без поля user",
        )
    try:
        user_payload = json.loads(user_field)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user внутри initData — невалидный JSON",
        )
    if not isinstance(user_payload, dict) or "id" not in user_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user внутри initData без id",
        )

    data["user"] = user_payload
    return data


def _user_dict_to_model(row: dict) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        avatar_url=row["avatar_url"],
        created_at=row["created_at"],
    )


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> User:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный или истёкший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    row = await db.get_user_by_id(user_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return _user_dict_to_model(row)


async def get_current_user_optional(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[User]:
    """Like get_current_user, but returns None instead of raising for guest requests.

    Use this for endpoints that work both for authenticated users and anonymous
    guests (e.g. recommendations with inline library, search, awards-style reads).
    Invalid/expired tokens still return None — let the caller decide whether to
    fall back to guest behaviour or treat it as unauthenticated.
    """
    if not creds or creds.scheme.lower() != "bearer":
        return None
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        return None
    row = await db.get_user_by_id(user_id)
    if not row:
        return None
    return _user_dict_to_model(row)
