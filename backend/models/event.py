"""Модели событийной аналитики (лёгкий self-hosted трекинг).

События пишутся фронтом батчами в ``POST /api/events`` и ботом напрямую в БД.
Имена строго из ``ALLOWED_EVENTS`` — это и защита от мусора/PII в ``name``, и
живой список того, что мы вообще меряем для kill-метрик эксперимента.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# Единый источник правды по именам событий. Любое имя вне набора отбрасывается
# на входе (явно > умно). Менять здесь — значит осознанно расширять воронку.
ALLOWED_EVENTS: frozenset[str] = frozenset({
    "app_open",                  # открытие приложения / новая сессия
    "session_start",             # синоним app_open для не-web источников
    "recommendation_requested",  # отправлен запрос на подбор (Tonight)
    "tonight_pick_viewed",       # показан экран с подобранными фильмами
    "availability_filter_used",  # переключён тоггл «только доступное»
    "availability_viewed",       # пользователь увидел бейджи доступности
    "movie_added",               # фильм добавлен в библиотеку (web или бот)
    "marked_watched",            # фильм отмечен просмотренным
    "share_opened",              # открыт экран шеринга списка
    "launch_clicked",            # клик «смотреть» — прокси «пошёл смотреть»
})

# Защитные лимиты, чтобы аналитика не стала вектором абьюза.
MAX_EVENTS_PER_BATCH = 50
MAX_PROPS_KEYS = 20


class EventIn(BaseModel):
    """Одно событие от клиента. ``user_id``/``source``/серверный ts ставит сервер."""
    name: str
    props: dict[str, Any] = Field(default_factory=dict)
    anon_id: Optional[str] = Field(None, max_length=64)
    # Клиентский timestamp (ISO) — необязательный, для отладки; сервер всегда
    # пишет свой ts, чтобы метрики не зависели от часов клиента.
    ts: Optional[str] = None


class EventBatch(BaseModel):
    """Батч событий за один POST (фронт буферизует и шлёт пачкой)."""
    events: list[EventIn] = Field(default_factory=list, max_length=MAX_EVENTS_PER_BATCH)
