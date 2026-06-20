"""Lightweight text-matching helpers shared by movie and book search.

These exist to fix a concrete problem: old / Russian titles are often buried
under more "popular" entries returned by TMDb / Google Books, so we re-rank
locally by how closely a candidate title matches what the user typed.

No new dependencies — ``difflib`` is stdlib. Kept deliberately small and
explicit: normalize → score → optionally pull a year out of the query.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional

# Punctuation/separators collapse to spaces so "Дюна: часть вторая" and
# "Дюна — часть вторая" normalize identically.
_NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")

# Год-квалификатор распознаём ТОЛЬКО в скобках — «Ирония судьбы (1975)». Голые
# числа в названии («Бегущий по лезвию 2049», «2001: A Space Odyssey», «2012»)
# годом релиза не являются, поэтому их не трогаем — иначе фильтр по году навредит.
_PAREN_YEAR_RE = re.compile(r"\(\s*(1[89]\d\d|20\d\d)\s*\)")


def normalize_title(text: Optional[str]) -> str:
    """Casefold, унифицировать ё→е, убрать пунктуацию и схлопнуть пробелы."""
    if not text:
        return ""
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = _NON_WORD_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip().casefold()


def title_score(query: Optional[str], candidate: Optional[str]) -> float:
    """Похожесть названий в диапазоне 0..1 (1.0 — точное совпадение).

    Поверх ``SequenceMatcher`` добавлен бонус за вхождение подстроки: запрос
    «Дюна» против «Дюна: Пророчество» должен стоять заметно выше случайного
    нечёткого совпадения, даже если ratio из-за длины невелик.
    """
    a, b = normalize_title(query), normalize_title(candidate)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ratio = SequenceMatcher(None, a, b).ratio()
    if a in b or b in a:
        ratio = max(ratio, 0.85)
    return ratio


def extract_year(text: str) -> tuple[str, Optional[int]]:
    """Вынуть год-квалификатор из «Название (1975)».

    Возвращает ``(title_without_year, year)``. Если скобочного года нет —
    ``(text, None)``. Название без года используется как поисковая строка, а год
    — как фильтр/тай-брейк.
    """
    m = _PAREN_YEAR_RE.search(text)
    if not m:
        return text.strip(), None
    year = int(m.group(1))
    cleaned = (text[: m.start()] + text[m.end():]).strip()
    cleaned = _WS_RE.sub(" ", cleaned)
    return (cleaned or text.strip()), year
