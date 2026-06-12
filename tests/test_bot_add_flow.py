"""Bot «+ Сохранить» flow: fast save, deferred enrichment, no destructive buttons.

The new flow saves the movie immediately (no waiting on the LLM), shows the
rating right away, and backfills the description + posts an intriguing «крючок»
in the background. Telegram ``query``/``message``/``context`` are tiny fakes
that record calls; we assert on the resulting DB state and the texts sent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend import database as db
from backend.models.movie import MovieBase
from backend.services.llm import llm_service
from handlers import callbacks


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
        self.markups: list = []  # каждый edit_message_reply_markup

    async def answer(self, *a, **kw):
        pass

    async def edit_message_reply_markup(self, reply_markup=None, **kw):
        self.markups.append(reply_markup)


class _FakeApp:
    """Захватывает фоновые задачи вместо реального планирования."""

    def __init__(self):
        self.tasks: list = []

    def create_task(self, coro, **kw):
        self.tasks.append(coro)
        return coro


class _FakeContext:
    def __init__(self):
        self.application = _FakeApp()
        self.user_data: dict = {}


def _movie(imdb_id: str, **over) -> MovieBase:
    base = dict(imdb_id=imdb_id, title="Test Movie", plot="Что-то происходит.",
                imdb_rating=7.349)
    base.update(over)
    return MovieBase(**base)


# ── fast save + deferred enrichment ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_add_saves_fast_then_enriches():
    user = await db.create_user(email="addflow1@tg.example.com", telegram_id=910001)
    query = _FakeQuery()
    ctx = _FakeContext()

    with patch("handlers.callbacks.omdb_service.get_movie_by_id",
               new=AsyncMock(return_value=_movie("tt_addflow1"))), \
         patch("handlers.callbacks.llm_service.describe_and_tease",
               new=AsyncMock(return_value=("Атмосферное кино.", "А что если всё не так?"))):
        await callbacks._handle_add(query, "tt_addflow1", user_id=user["id"], context=ctx)

        # Saved immediately, WITHOUT waiting on the LLM (description still empty).
        saved = await db.get_user_movie_by_imdb_id("tt_addflow1", user["id"])
        assert saved is not None
        # source — тип записи; канал рекомендации (rec_source) для карточки из
        # текстового поиска не пишется: источника-ссылки у неё нет.
        assert saved.source == "personal"
        assert saved.rec_source is None
        assert saved.description is None

        # Confirmation shows the rounded rating right away.
        assert any("Test Movie" in r and "7.3" in r for r in query.message.replies)

        # A loader was shown before the final keyboard (≥2 markup edits).
        assert len(query.markups) >= 2

        # Exactly one background task scheduled; run it to verify enrichment.
        assert len(ctx.application.tasks) == 1
        await ctx.application.tasks[0]

    enriched = await db.get_user_movie_by_imdb_id("tt_addflow1", user["id"])
    assert enriched.description == "Атмосферное кино."
    assert any("А что если всё не так?" in r for r in query.message.replies)


@pytest.mark.asyncio
async def test_handle_add_existing_is_instant_and_skips_omdb():
    user = await db.create_user(email="addflow2@tg.example.com", telegram_id=910002)
    await db.add_movie(_movie("tt_addflow2"), user_id=user["id"], source="telegram")

    query = _FakeQuery()
    ctx = _FakeContext()
    omdb = AsyncMock()
    with patch("handlers.callbacks.omdb_service.get_movie_by_id", new=omdb):
        await callbacks._handle_add(query, "tt_addflow2", user_id=user["id"], context=ctx)

    assert any("уже в тво" in r for r in query.message.replies)
    omdb.assert_not_awaited()              # no network for a known movie
    assert ctx.application.tasks == []     # nothing to enrich


@pytest.mark.asyncio
async def test_handle_add_omdb_failure_restores_save_button():
    user = await db.create_user(email="addflow3@tg.example.com", telegram_id=910003)
    query = _FakeQuery()
    ctx = _FakeContext()

    with patch("handlers.callbacks.omdb_service.get_movie_by_id",
               new=AsyncMock(return_value=None)):
        await callbacks._handle_add(query, "tt_addflow3", user_id=user["id"], context=ctx)

    assert await db.get_user_movie_by_imdb_id("tt_addflow3", user["id"]) is None
    assert any("не получилось" in r.lower() for r in query.message.replies)
    # loader shown, then the «+ Сохранить» button restored for a retry.
    assert query.markups and query.markups[-1] is not None
    assert ctx.application.tasks == []


# ── keyboard: no destructive buttons after an explicit save ──────────────────


def test_saved_keyboard_has_no_destructive_buttons():
    with patch("handlers.callbacks.MINI_APP_URL", "https://app.example"):
        kb = callbacks._saved_confirmation_keyboard()
    texts = [b.text for row in kb.inline_keyboard for b in row]
    assert texts == ["📖 Открыть в Lentochka"]
    assert "Удалить" not in texts and "Не тот фильм?" not in texts


def test_saved_keyboard_is_none_without_mini_app():
    with patch("handlers.callbacks.MINI_APP_URL", ""):
        assert callbacks._saved_confirmation_keyboard() is None


# ── LLM output parsing ───────────────────────────────────────────────────────


def test_parse_description_and_hook_labeled():
    d, h = llm_service._parse_description_and_hook(
        "ОПИСАНИЕ: Большое кино про маленьких людей.\nКРЮЧОК: А ты бы решился?"
    )
    assert d == "Большое кино про маленьких людей."
    assert h == "А ты бы решился?"


def test_parse_description_and_hook_fallback_to_description():
    d, h = llm_service._parse_description_and_hook("Просто текст без меток")
    assert d == "Просто текст без меток"
    assert h == ""
