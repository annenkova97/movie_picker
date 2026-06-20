from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class User(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleLogin(BaseModel):
    id_token: str


class TelegramWebAppLogin(BaseModel):
    # Сырая строка initData как её отдал Telegram.WebApp.initData во фронте.
    # Подпись и user-объект мы парсим/проверяем на сервере.
    init_data: str


class TelegramWidgetLogin(BaseModel):
    """Поля, которые отдаёт Telegram Login Widget в onauth-колбэке.

    Подпись (``hash``) и timestamp (``auth_date``) обязательны; остальное —
    то, что Telegram прислал, может варьироваться (нет username, нет фото).
    """
    id: int
    auth_date: int
    hash: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user: User


class UserSettings(BaseModel):
    """Пользовательские настройки доступности (регион + стриминговые сервисы).

    ``region`` — двухбуквенный код страны для TMDb watch-providers (RU/US/…).
    ``streaming_services`` — id провайдеров TMDb, на которые подписан юзер;
    пустой список = «фильтра нет, показывать всё».
    """
    region: str = "RU"
    streaming_services: list[int] = []


class UserSettingsUpdate(BaseModel):
    """Частичное обновление настроек: задаётся только то, что меняем."""
    region: Optional[str] = Field(None, min_length=2, max_length=2)
    streaming_services: Optional[list[int]] = None
