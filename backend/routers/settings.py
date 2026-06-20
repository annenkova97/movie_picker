"""Пользовательские настройки доступности (регион + стриминговые сервисы).

Серверное хранилище настроек, чтобы они ехали за пользователем между
устройствами (гостевые настройки фронт держит в localStorage сам).
"""
from fastapi import APIRouter, Depends

from backend import database as db
from backend.auth import get_current_user
from backend.models import User, UserSettings, UserSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=UserSettings)
async def read_settings(current_user: User = Depends(get_current_user)):
    return UserSettings(**await db.get_user_settings(current_user.id))


@router.patch("", response_model=UserSettings)
async def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
):
    settings = await db.update_user_settings(
        current_user.id,
        region=payload.region.upper() if payload.region else None,
        streaming_services=payload.streaming_services,
    )
    return UserSettings(**settings)
