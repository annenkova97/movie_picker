"""Единая точка поиска фильма по названию: TMDB (RU) → OMDB → OMDB-после-перевода.

Все «введи название фильма»-сценарии бота — ``/search``, ``/add`` и свободный
текст в чате — ходят сюда. Это:

1. Даёт одинаковое поведение в трёх местах (раньше /search и /add не понимали
   кириллицу вообще).
2. Прозрачно подключает TMDB, если есть ``TMDB_API_KEY``: TMDB
   ищет на русском, выдаёт русские названия и IMDb id'ы, по которым мы потом
   тянем полную метадату из OMDB.
3. Без TMDB-ключа — пайплайн откатывается на OMDB + LLM-перевод, как было.
"""

from __future__ import annotations

import re
from typing import Optional

from backend.models.movie import MovieBase, OMDBSearchResult
from backend.services.llm import llm_service
from backend.services.omdb import omdb_service
from backend.services.tmdb import is_tmdb_key, tmdb_service


CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")


def has_cyrillic(text: str) -> bool:
    return bool(CYRILLIC_RE.search(text))


async def get_movie_by_key(key: str) -> Optional[MovieBase]:
    """Полная ``MovieBase`` по внешнему ключу — диспетчер по провайдеру.

    Зеркало ``book_search.get_book_by_key``: ``tmdb:…`` → метадата из TMDb (для
    фильмов без IMDb id), всё остальное (``tt…``) → OMDB по IMDb id.
    """
    if is_tmdb_key(key):
        return await tmdb_service.get_by_key(key)
    return await omdb_service.get_movie_by_id(key)


async def search_title(query: str) -> list[OMDBSearchResult]:
    """Ищет фильмы по названию — возвращает список карточек для UI.

    Порядок попыток:
    - Кириллица + TMDB включён → TMDB на ru-RU (русские названия в UI).
    - OMDB напрямую с исходным запросом.
    - Если запрос кириллический и пусто — LLM-перевод → OMDB ещё раз.
    """
    query = query.strip()
    if not query:
        return []

    cyrillic = has_cyrillic(query)

    if cyrillic and tmdb_service.enabled:
        # search_any = фильмы + сериалы: OMDB по кириллице не находит сериалы
        # вовсе, так что для русских названий сериалов это единственный путь.
        results = await tmdb_service.search_any(query)
        if results:
            return results

    results = await omdb_service.search_movies(query)
    if results:
        return results

    if not cyrillic:
        return []

    translated = await _translate_safe(query)
    if not translated:
        return []

    return await omdb_service.search_movies(translated)


async def find_movie_by_query(query: str) -> Optional[MovieBase]:
    """Resolve единичный фильм по запросу — для ``/add``.

    Возвращает полную ``MovieBase`` из OMDB или None. Алгоритм:
    1. Если в запросе IMDb id (``tt...``) — берём напрямую.
    2. Иначе: пробуем точный match OMDB (``?t=...``). Для англоязычных
       названий это самый аккуратный путь.
    3. Если пусто и кириллица — идём через ``search_title`` (TMDB → OMDB)
       и берём первый результат, докачивая полную метадату по imdb_id.
    """
    query = query.strip()
    if not query:
        return None

    if query.startswith("tt") and query[2:].isdigit():
        return await get_movie_by_key(query)

    movie = await omdb_service.get_movie_by_title(query)
    if movie:
        return movie

    candidates = await search_title(query)
    if not candidates:
        return None

    # Кандидат может быть TMDb-only (ключ ``tmdb:…``) — диспетчеризуем.
    return await get_movie_by_key(candidates[0].imdb_id)


async def _translate_safe(query: str) -> str:
    """LLM-перевод названия с гарантией не упасть. Возвращает '' на любую ошибку
    или если перевод совпал с оригиналом (бессмысленно дёргать OMDB ещё раз)."""
    try:
        translated = (await llm_service.translate_movie_title(query)).strip()
    except Exception as exc:
        print(f"[title_search] translate failed: {exc}")
        return ""

    if not translated or translated.lower() == query.lower():
        return ""
    return translated
