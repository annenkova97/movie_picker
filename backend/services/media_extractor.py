"""Extract BOTH films and books mentioned in a free-form post.

The bot's forwarded-post flow used to recognise only films (``extract_movies``
in ``instagram_reader``). This adds a single LLM call that classifies every
mention as a film or a book, so a forwarded book recommendation gets saved too.

One call returns a typed list; the caller resolves films via OMDB
(``resolve_movies``) and books via Google Books/Open Library (``resolve_books``).

Reuses ``llm_service``'s Anthropic client (DRY) and the ``MovieInfo`` shape so
the existing movie resolver works unchanged.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from backend.services.instagram_reader import MovieInfo
from backend.services.llm import llm_service


@dataclass
class BookInfo:
    title_ru: str
    title_en: str
    author: str = ""


_SYSTEM_PROMPT = """\
You extract films AND books mentioned in a social-media post (text in any \
language). Return ONLY a JSON array, no markdown, no commentary.

Each element must have exactly these fields:
- "kind": "film" or "book"
- "title_ru": the title in Russian
- "title_en": the official English/original title (for books, the original \
title in its original language is fine)
- "author": for books — the author's name; for films — empty string ""

Rules:
- Classify each mention as a film or a book by context (a поэт/писатель/роман/\
стихи/книга → book; режиссёр/сериал/фильм/кино → film).
- For films, give the real official English title as on IMDb. Do not transliterate.
- For books, "author" is important — fill it whenever the post names the author.
- If nothing is mentioned, return [].
"""


async def extract_media(text: str) -> tuple[list[MovieInfo], list[BookInfo]]:
    """Return ``(films, books)`` extracted from ``text``. Empty lists on miss."""
    text = (text or "").strip()
    if not text:
        return [], []

    message = await llm_service.client.messages.create(
        model=llm_service.model,
        max_tokens=900,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = (message.content[0].text or "").strip()

    items = _parse_json_array(raw)
    films: list[MovieInfo] = []
    books: list[BookInfo] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        title_ru = (it.get("title_ru") or "").strip()
        title_en = (it.get("title_en") or "").strip()
        if not title_ru and not title_en:
            continue
        if (it.get("kind") or "").lower() == "book":
            books.append(BookInfo(
                title_ru=title_ru, title_en=title_en,
                author=(it.get("author") or "").strip(),
            ))
        else:
            films.append(MovieInfo(title_ru=title_ru, title_en=title_en, description="", quote=""))
    return films, books


def _parse_json_array(raw: str) -> list:
    """Best-effort JSON-array parse, tolerant of markdown fences / stray text."""
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []
