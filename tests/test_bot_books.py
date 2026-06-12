"""Telegram bot: books in forwarded posts + diary rating/notes on the bot.

Services (LLM, book search) are stubbed so nothing hits the network. Telegram
``query``/``update``/``context`` objects are tiny fakes that record calls — we
assert on the resulting DB state, which is the part that matters.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend import database as db
from backend.models.book import BookBase, BookSearchResult
from backend.models.movie import MovieBase


# ── fakes ────────────────────────────────────────────────────────────────────


class _FakeMessage:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text, **kw):
        self.replies.append(text)
        return _FakeMessage()


class _FakeQuery:
    def __init__(self):
        self.message = _FakeMessage()
        self.edited_text: str | None = None
        self.markup_edits = 0

    async def edit_message_text(self, text, **kw):
        self.edited_text = text

    async def edit_message_reply_markup(self, **kw):
        self.markup_edits += 1


class _FakeUser:
    def __init__(self, tg_id):
        self.id = tg_id
        self.first_name = "Tg"
        self.last_name = ""
        self.username = "tg"


class _FakeContext:
    def __init__(self):
        self.user_data: dict = {}


def _fake_anthropic_message(text: str):
    content = type("C", (), {"text": text})()
    return type("M", (), {"content": [content]})()


# ── extract_media ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_media_splits_films_and_books():
    from backend.services.media_extractor import extract_media

    payload = (
        '[{"kind":"film","title_ru":"Брат","title_en":"Brother","author":""},'
        '{"kind":"book","title_ru":"Часть речи","title_en":"A Part of Speech",'
        '"author":"Иосиф Бродский"}]'
    )
    with patch(
        "backend.services.media_extractor.llm_service.client.messages.create",
        new=AsyncMock(return_value=_fake_anthropic_message(payload)),
    ):
        films, books = await extract_media("какой-то пост про кино и стихи")

    assert [f.title_en for f in films] == ["Brother"]
    assert len(books) == 1
    assert books[0].author == "Иосиф Бродский"


@pytest.mark.asyncio
async def test_extract_media_empty_text_skips_llm():
    from backend.services.media_extractor import extract_media

    with patch(
        "backend.services.media_extractor.llm_service.client.messages.create",
        new=AsyncMock(),
    ) as create:
        films, books = await extract_media("   ")

    assert films == [] and books == []
    create.assert_not_awaited()


# ── resolve_books ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_books_uses_author_query_and_resolves():
    from backend.services.book_resolver import resolve_books
    from backend.services.media_extractor import BookInfo

    hit = BookSearchResult(work_key="gb:abc", title="Часть речи", author="Бродский",
                           year="1977", cover_url=None)
    base = BookBase(work_key="gb:abc", title="Часть речи", authors=["Иосиф Бродский"])

    search = AsyncMock(return_value=[hit])
    with patch("backend.services.book_resolver.book_search.search_books", new=search), \
         patch("backend.services.book_resolver.book_search.get_book_by_key",
               new=AsyncMock(return_value=base)):
        resolved, unmatched = await resolve_books(
            [BookInfo(title_ru="Часть речи", title_en="", author="Иосиф Бродский")]
        )

    assert [b.work_key for b in resolved] == ["gb:abc"]
    assert unmatched == []
    # author folded into the query — that's what makes Brodsky resolve.
    search.assert_awaited_once_with("Часть речи Иосиф Бродский")


@pytest.mark.asyncio
async def test_resolve_books_reports_unmatched():
    from backend.services.book_resolver import resolve_books
    from backend.services.media_extractor import BookInfo

    with patch("backend.services.book_resolver.book_search.search_books",
               new=AsyncMock(return_value=[])):
        resolved, unmatched = await resolve_books(
            [BookInfo(title_ru="Неведомая книга", title_en="", author="")]
        )

    assert resolved == []
    assert unmatched == ["Неведомая книга"]


# ── bot callbacks: add book + diary rating/note ──────────────────────────────


@pytest.mark.asyncio
async def test_handle_add_book_saves_to_library():
    from handlers import callbacks

    user = await db.create_user(email="botbook1@tg.example.com", telegram_id=900001)
    base = BookBase(work_key="gb:xyz", title="Зов Ктулху", authors=["Лавкрафт"])

    query = _FakeQuery()
    with patch("handlers.callbacks.book_search.get_book_by_key",
               new=AsyncMock(return_value=base)):
        await callbacks._handle_add_book(query, "gb:xyz", user_id=user["id"])

    saved = await db.get_user_book_by_work_key("gb:xyz", user["id"])
    assert saved is not None
    assert saved.title == "Зов Ктулху"
    assert saved.source == "personal"


@pytest.mark.asyncio
async def test_bot_rating_then_note_writes_diary():
    from handlers import callbacks

    # User identified by telegram_id (how the note handler resolves them).
    user = await db.create_user(email="botrate@tg.example.com", telegram_id=900002)
    movie = await db.add_movie(
        MovieBase(imdb_id="tt0133093", title="The Matrix"),
        user_id=user["id"], source="telegram",
    )

    # 1) tap a star → rating saved + note prompt armed
    query = _FakeQuery()
    ctx = _FakeContext()
    await callbacks._handle_rate(query, f"movie:{movie.id}:5", user_id=user["id"], context=ctx)

    rated = await db.get_user_movie_by_id(movie.id, user["id"])
    assert rated.user_rating == 5
    assert ctx.user_data["await_note"] == ("movie", movie.id)

    # 2) reply with a note → saved, processing stopped
    from telegram.ext import ApplicationHandlerStop

    update = type("U", (), {
        "message": type("Msg", (), {
            "text": "Лучшее из трилогии",
            "reply_text": AsyncMock(),
        })(),
        "effective_user": _FakeUser(900002),
    })()

    with pytest.raises(ApplicationHandlerStop):
        await callbacks.note_reply_handler(update, ctx)

    noted = await db.get_user_movie_by_id(movie.id, user["id"])
    assert noted.user_note == "Лучшее из трилогии"
    assert "await_note" not in ctx.user_data


@pytest.mark.asyncio
async def test_note_handler_ignores_when_not_awaiting():
    """A normal reply (no pending note) passes through without raising/saving."""
    from handlers import callbacks

    ctx = _FakeContext()  # no await_note
    update = type("U", (), {
        "message": type("Msg", (), {"text": "просто текст", "reply_text": AsyncMock()})(),
        "effective_user": _FakeUser(900003),
    })()

    # Returns quietly (no ApplicationHandlerStop) so text_handler can run.
    assert await callbacks.note_reply_handler(update, ctx) is None


# ── webhook route ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_rejects_bad_secret(client):
    # In tests TELEGRAM_WEBHOOK_SECRET is empty → every secret is rejected.
    r = await client.post("/telegram/webhook/anything", json={"update_id": 1})
    assert r.status_code == 403
