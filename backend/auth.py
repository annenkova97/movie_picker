"""Аутентификация: хэш паролей, JWT, проверка Google ID-токена, зависимость FastAPI."""
from __future__ import annotations

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from backend import database as db
from backend.config import JWT_SECRET, JWT_EXPIRES_DAYS, JWT_ALGORITHM, GOOGLE_CLIENT_ID
from backend.models import User


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
