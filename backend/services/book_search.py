"""Единая точка поиска книг: Google Books → Wikidata → Open Library.

Зеркало ``services/title_search.py`` для фильмов. Google Books идёт первым —
он сильно лучше находит русскоязычные книги (для кириллицы добавляем
``langRestrict=ru``, а если он перефильтровал в пустоту — повторяем без него).

Если Google молчит (исчерпана анонимная квота → 429, или просто ничего нет),
откатываемся на источники, независимые от его квоты: сначала Wikidata (сильна
по-русски, без ключа и дневного лимита), затем Open Library.

Выдачу локально ре-ранжируем по близости названия (``text_match``): Google
часто ставит учебники/дубли-издания/переводы выше нужной классики, особенно для
старых русских книг. Детали тянем по префиксу ключа: ``gb:…`` → Google Books,
``wd:…`` → Wikidata, ``OL…W`` → Open Library.
"""

from __future__ import annotations

from typing import Optional

from backend.models.book import BookBase, BookSearchResult
from backend.services.googlebooks import googlebooks_service, is_google_key
from backend.services.openlibrary import openlibrary_service
from backend.services.text_match import normalize_title, title_score
from backend.services.title_search import has_cyrillic
from backend.services.wikidata import is_wikidata_key, wikidata_service


def _has_operators(query: str) -> bool:
    return "intitle:" in query or "inauthor:" in query


def _significant_tokens(text: Optional[str]) -> set[str]:
    """Слова длиной ≥3 символов. Короткие («и», «в», инициалы) отбрасываем —
    иначе токен «и» из «Война и мир» ложно совпал бы с автором «И. Фамилия»."""
    return {t for t in normalize_title(text).split() if len(t) >= 3}


def _author_matches(query: str, author: Optional[str]) -> bool:
    """Пересекается ли запрос с именем автора по значимым токенам.

    Для «Бродский» это True у его книг (автор «Иосиф Бродский») и False у книг
    *про* него (автор — кто-то другой, «Бродский» лишь в названии)."""
    return bool(author and (_significant_tokens(query) & _significant_tokens(author)))


def _looks_like_author(query: str) -> bool:
    """Похоже ли на имя автора: 1–2 значимых слова (фамилия или «Имя Фамилия»).
    Длинные строки почти всегда названия — для них inauthor бессмыслен."""
    return 1 <= len(_significant_tokens(query)) <= 2


async def _google(query: str, prefer_lang: Optional[str]) -> list[BookSearchResult]:
    """Google Books с подстраховкой по языку.

    ``langRestrict=ru`` поднимает русские издания над переводами, но Google
    далеко не всем русским томам проставляет язык — под фильтром они выпадают,
    и автор вроде «Бродский» может вернуть пусто. Поэтому при пустом ответе
    повторяем тот же запрос без ограничения языка, прежде чем сдаваться.
    """
    results = await googlebooks_service.search_books(query, prefer_lang=prefer_lang)
    if not results and prefer_lang:
        results = await googlebooks_service.search_books(query)
    return results


def _merge(primary: list[BookSearchResult], secondary: list[BookSearchResult]) -> list[BookSearchResult]:
    """``primary`` впереди, затем ``secondary`` без дублей по ``work_key``."""
    seen = {r.work_key for r in primary}
    return list(primary) + [r for r in secondary if r.work_key not in seen]


def _rerank(results: list[BookSearchResult], key: str) -> list[BookSearchResult]:
    """Отсортировать по релевантности к ``key`` (лучшее — выше).

    Главный критерий — совпадение по АВТОРУ: для запроса-автора («Бродский»)
    его произведения должны стоять строго выше книг, просто ОЗАГЛАВЛЕННЫХ
    запросом (книги про него, где автор другой). Дальше — близость названия.
    Сорт стабилен, поэтому внутри равных сохраняется порядок источника
    (у Google/inauthor он ≈ по популярности)."""
    return [
        r for _, r in sorted(
            enumerate(results),
            key=lambda iv: (
                not _author_matches(key, iv[1].author),  # author-совпадения первыми
                -title_score(key, iv[1].title),
                iv[0],
            ),
        )
    ]


async def search_books(
    query: str, *, rank_query: Optional[str] = None,
) -> list[BookSearchResult]:
    """Карточки книг для UI. Google Books первым, Open Library — фолбэк.

    ``rank_query`` — по какой строке ранжировать (по умолчанию сам ``query``).
    Резолвер передаёт сюда чистое название, даже когда ``query`` собран из
    операторов ``intitle:/inauthor:`` для recall'а.
    """
    query = query.strip()
    if not query:
        return []

    rank_by = rank_query or query
    prefer_lang = "ru" if has_cyrillic(query) else None
    results = await _google(query, prefer_lang)

    # Запрос похож на автора → подмешиваем книги, где он именно АВТОР
    # (``inauthor:``). Обычный запрос «Бродский» тонет в книгах *про* него;
    # inauthor достаёт *написанные им* произведения (у Google — по популярности),
    # а ре-ранжирование ниже ставит их выше. Только для «чистых» запросов:
    # из резолвера приходит query с Google-операторами — его не трогаем.
    if not _has_operators(query) and _looks_like_author(query):
        by_author = await _google(f'inauthor:"{query}"', prefer_lang)
        if by_author:
            results = _merge(by_author, results)

    # Старые/редкие книги: если до сих пор пусто — строгий intitle перед
    # откатом на бесключевые источники.
    if not results and not _has_operators(query):
        results = await _google(f"intitle:{query}", prefer_lang)

    # Google молчит (квота/429 или ничего не нашёл) → независимые от него
    # источники. Wikidata сильнее по-русски, поэтому идёт перед Open Library.
    # Им отдаём человекочитаемую строку (rank_by), а не Google-операторы из query.
    if not results:
        results = await wikidata_service.search_books(rank_by)

    if not results:
        results = await openlibrary_service.search_books(rank_by)
        # Запрос-имя: общий q у Open Library отдаёт книги *про* автора;
        # отдельный запрос по полю автора достаёт *написанные им* — ставим их
        # вперёд (ре-ранжирование закрепит), чтобы выдача была не только «о нём».
        if _looks_like_author(rank_by):
            by_author = await openlibrary_service.search_books(rank_by, by_author=True)
            results = _merge(by_author, results)

    return _rerank(results, rank_by)


async def get_book_by_key(work_key: str) -> Optional[BookBase]:
    """Полные метаданные книги по ключу. Диспатч по префиксу провайдера."""
    if is_google_key(work_key):
        return await googlebooks_service.get_book_by_key(work_key)
    if is_wikidata_key(work_key):
        return await wikidata_service.get_book_by_key(work_key)
    return await openlibrary_service.get_book_by_key(work_key)
