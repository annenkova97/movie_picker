"""Источник рекомендации: rec_source + source_url из ссылок, откат «Не тот»/«Не добавлять».

Карточки, рождённые из ссылки (Reel, пост канала), регистрируют источник в
``handlers.source_context``; сохранение пишет его в rec_source/source_url.
Набранные руками названия сохраняются без источника. Авто-сохранённый из
ссылки фильм можно откатить кнопками «Не тот» (удалить + похожие варианты)
и «Не добавлять» (просто удалить).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend import database as db
from backend.models.movie import MovieBase, OMDBSearchResult
from handlers import callbacks
from handlers.source_context import get_source, remember_source


# ── fakes ────────────────────────────────────────────────────────────────────


class _FakeChat:
    def __init__(self, chat_id: int):
        self.id = chat_id


class _FakeMessage:
    def __init__(self, chat_id: int = 111):
        self.replies: list[str] = []
        self.chat = _FakeChat(chat_id)

    async def reply_text(self, text, **kw):
        self.replies.append(text)
        return _FakeMessage(self.chat.id)

    async def reply_photo(self, photo, caption="", **kw):
        self.replies.append(caption)
        return _FakeMessage(self.chat.id)


class _FakeQuery:
    def __init__(self, chat_id: int = 111):
        self.message = _FakeMessage(chat_id)
        self.markups: list = []

    async def answer(self, *a, **kw):
        pass

    async def edit_message_reply_markup(self, reply_markup=None, **kw):
        self.markups.append(reply_markup)


class _FakeApp:
    def __init__(self):
        self.tasks: list = []

    def create_task(self, coro, **kw):
        coro.close()  # не исполняем фоновые задачи в этих тестах
        self.tasks.append(coro)
        return coro


class _FakeContext:
    def __init__(self):
        self.application = _FakeApp()
        self.user_data: dict = {}


class _FakeTgUser:
    def __init__(self, tg_id: int):
        self.id = tg_id
        self.first_name = "Test"
        self.last_name = None
        self.username = "test"


def _movie(imdb_id: str, **over) -> MovieBase:
    base = dict(imdb_id=imdb_id, title="Linked Movie", imdb_rating=7.5)
    base.update(over)
    return MovieBase(**base)


def _buttons(markup) -> list[str]:
    return [b.text for row in markup.inline_keyboard for b in row]


# ── source registry → сохранение ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_add_uses_registered_link_source():
    user = await db.create_user(email="src1@tg.example.com", telegram_id=920001)
    query = _FakeQuery(chat_id=201)
    ctx = _FakeContext()

    reel = "https://instagram.com/reel/abc/"
    remember_source(201, "tt_src1", "instagram", reel)

    with patch("handlers.callbacks.get_movie_by_key",
               new=AsyncMock(return_value=_movie("tt_src1"))):
        await callbacks._handle_add(query, "tt_src1", user_id=user["id"], context=ctx)

    saved = await db.get_user_movie_by_imdb_id("tt_src1", user["id"])
    assert saved.source == "personal"
    assert saved.rec_source == "instagram"
    assert saved.source_url == reel
    # Карточка из ссылки получает кнопки отката, а не «Открыть в Lentochka».
    assert _buttons(query.markups[-1]) == ["Не тот", "Не добавлять"]


@pytest.mark.asyncio
async def test_handle_add_without_link_source_keeps_personal():
    user = await db.create_user(email="src2@tg.example.com", telegram_id=920002)
    query = _FakeQuery(chat_id=202)  # ничего не регистрировали для этого чата
    ctx = _FakeContext()

    with patch("handlers.callbacks.get_movie_by_key",
               new=AsyncMock(return_value=_movie("tt_src2"))), \
         patch("handlers.callbacks.MINI_APP_URL", "https://app.example"):
        await callbacks._handle_add(query, "tt_src2", user_id=user["id"], context=ctx)

    saved = await db.get_user_movie_by_imdb_id("tt_src2", user["id"])
    assert saved.rec_source is None
    assert saved.source_url is None
    assert "Не тот" not in _buttons(query.markups[-1])


# ── авто-добавление из ссылки ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auto_add_movie_saves_with_source():
    tg_user = _FakeTgUser(920003)
    msg = _FakeMessage(chat_id=203)
    ctx = _FakeContext()

    movie, existed = await callbacks.auto_add_movie(
        msg, ctx, tg_user, _movie("tt_auto1", plot="Сюжет."),
        rec_source="telegram", source_url="https://t.me/channel/42",
    )

    assert not existed
    assert movie.rec_source == "telegram"
    assert movie.source_url == "https://t.me/channel/42"
    assert len(ctx.application.tasks) == 1  # фоновая догенерация запланирована

    # Повторное авто-добавление узнаёт дубликат.
    movie2, existed2 = await callbacks.auto_add_movie(
        msg, ctx, tg_user, _movie("tt_auto1"),
        rec_source="telegram", source_url=None,
    )
    assert existed2 and movie2.id == movie.id


# ── откат: «Не добавлять» и «Не тот» ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_undo_deletes_movie():
    user = await db.create_user(email="src4@tg.example.com", telegram_id=920004)
    movie = await db.add_movie(_movie("tt_undo1"), user_id=user["id"])

    query = _FakeQuery(chat_id=204)
    await callbacks._handle_undo(query, movie.id, user_id=user["id"])

    assert await db.get_user_movie_by_imdb_id("tt_undo1", user["id"]) is None
    # Кнопка «+ Сохранить» вернулась на карточку.
    assert _buttons(query.markups[-1]) == ["+ Сохранить"]
    assert any("не сохраняю" in r for r in query.message.replies)


@pytest.mark.asyncio
async def test_handle_wrong_deletes_and_offers_alternatives():
    user = await db.create_user(email="src5@tg.example.com", telegram_id=920005)
    movie = await db.add_movie(_movie("tt_wrong1"), user_id=user["id"])
    remember_source(205, "tt_wrong1", "instagram", "https://instagram.com/reel/xyz/")

    alternatives = [
        OMDBSearchResult(imdb_id="tt_alt1", title="Linked Movie II", year="2020"),
        OMDBSearchResult(imdb_id="tt_wrong1", title="Linked Movie", year="2010"),
    ]
    query = _FakeQuery(chat_id=205)
    with patch("handlers.callbacks.search_title",
               new=AsyncMock(return_value=alternatives)):
        await callbacks._handle_wrong(query, movie.id, user_id=user["id"])

    assert await db.get_user_movie_by_imdb_id("tt_wrong1", user["id"]) is None
    assert any("похожие варианты" in r.lower() for r in query.message.replies)
    # Источник переехал на альтернативную карточку — добавление с неё
    # сохранит тот же instagram-источник.
    assert get_source(205, "tt_alt1").rec_source == "instagram"


@pytest.mark.asyncio
async def test_handle_wrong_when_already_deleted():
    user = await db.create_user(email="src6@tg.example.com", telegram_id=920006)
    query = _FakeQuery(chat_id=206)
    await callbacks._handle_wrong(query, 999999, user_id=user["id"])
    assert any("уже нет" in r.lower() for r in query.message.replies)


# ── ссылка на оригинал пересланного поста ────────────────────────────────────


def test_origin_post_url_public_channel():
    from handlers.forward import _origin_post_url

    class _Chat:
        username = "kinochannel"

    class _Origin:
        chat = _Chat()
        message_id = 77

    class _Msg:
        forward_origin = _Origin()

    assert _origin_post_url(_Msg()) == "https://t.me/kinochannel/77"


def test_origin_post_url_private_or_user_forward():
    from handlers.forward import _origin_post_url

    class _Msg:
        forward_origin = None

    assert _origin_post_url(_Msg()) is None

    class _Chat:
        username = None

    class _Origin:
        chat = _Chat()
        message_id = 5

    class _Msg2:
        forward_origin = _Origin()

    assert _origin_post_url(_Msg2()) is None
