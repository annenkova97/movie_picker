"""Память «откуда пришла карточка» между отправкой и нажатием кнопки.

Кнопка «Добавить» несёт в callback_data только ``add:<imdb_id>`` (лимит
Telegram — 64 байта), поэтому ссылку на источник (Reel, пост в канале) туда
не положить. Вместо этого хендлеры, отправляя карточку, регистрируют здесь
контекст по ``(chat_id, key)``, а ``callback_handler`` достаёт его при
сохранении.

Реестр процессный и нестрогий: после рестарта контекст теряется, и фильм
просто сохранится без источника — это не критичный путь.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import NamedTuple, Optional


class SourceCtx(NamedTuple):
    rec_source: str            # instagram / telegram
    source_url: Optional[str]  # ссылка на Reel / пост; None, если её нет


_MAX_ENTRIES = 500
_registry: OrderedDict[tuple[int, str], SourceCtx] = OrderedDict()


def remember_source(
    chat_id: int, key: str, rec_source: str, source_url: Optional[str]
) -> None:
    """Запоминает источник карточки. ``key`` — imdb_id или work_key книги."""
    full_key = (chat_id, key)
    _registry.pop(full_key, None)
    _registry[full_key] = SourceCtx(rec_source, source_url)
    while len(_registry) > _MAX_ENTRIES:
        _registry.popitem(last=False)


def get_source(chat_id: int, key: str) -> Optional[SourceCtx]:
    """Источник карточки, если он известен. Не удаляет запись — после
    «Не добавлять» пользователь может сохранить фильм повторно."""
    return _registry.get((chat_id, key))
