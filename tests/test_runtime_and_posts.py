"""Длительность из OMDB, эвристика «вставленный пост», комментарии к Reels."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend import database as db
from backend.models.movie import MovieBase
from backend.services.omdb import omdb_service


# ── runtime из OMDB ──────────────────────────────────────────────────────────


def test_parse_movie_extracts_runtime_minutes():
    movie = omdb_service._parse_movie({
        "imdbID": "tt0468569", "Title": "The Dark Knight",
        "Runtime": "152 min",
    })
    assert movie.runtime == 152


def test_parse_movie_runtime_na_is_zero():
    """0 — маркер «проверено, OMDB не знает» (бэкфилл не перепроверяет)."""
    movie = omdb_service._parse_movie({
        "imdbID": "tt000", "Title": "X", "Runtime": "N/A",
    })
    assert movie.runtime == 0


@pytest.mark.asyncio
async def test_runtime_persists_through_db():
    user = await db.create_user(email="rt1@tg.example.com", telegram_id=930001)
    movie = await db.add_movie(
        MovieBase(imdb_id="tt_rt1", title="Timed", runtime=148),
        user_id=user["id"],
    )
    assert movie.runtime == 148

    saved = await db.get_user_movie_by_imdb_id("tt_rt1", user["id"])
    assert saved.runtime == 148


@pytest.mark.asyncio
async def test_runtime_backfill_helpers():
    user = await db.create_user(email="rt2@tg.example.com", telegram_id=930002)
    await db.add_movie(
        MovieBase(imdb_id="tt_rt_missing", title="No runtime yet"),
        user_id=user["id"],
    )

    missing = await db.get_imdb_ids_missing_runtime()
    assert "tt_rt_missing" in missing

    changed = await db.set_runtime_by_imdb("tt_rt_missing", 95)
    assert changed == 1
    assert "tt_rt_missing" not in await db.get_imdb_ids_missing_runtime()

    saved = await db.get_user_movie_by_imdb_id("tt_rt_missing", user["id"])
    assert saved.runtime == 95


# ── «вставленный пост» в свободном тексте ────────────────────────────────────


def test_looks_like_post_heuristic():
    from handlers.forward import looks_like_post

    assert not looks_like_post("Inception")
    assert not looks_like_post("что-то лёгкое и смешное на вечер")
    assert looks_like_post("Подборка фильмов:\n1. Начало\n2. Интерстеллар")
    assert looks_like_post("х" * 250)


@pytest.mark.asyncio
async def test_text_handler_routes_long_text_to_post_pipeline():
    from handlers.recommend import text_handler

    class _Msg:
        text = "Топ фильмов осени:\n«Анора»\n«Субстанция»"

        async def reply_text(self, *a, **kw):
            raise AssertionError("должен уйти в пост-пайплайн, а не в поиск")

    class _Update:
        message = _Msg()

    pipeline = AsyncMock()
    with patch("handlers.forward.process_pasted_text", new=pipeline), \
         patch("handlers.recommend.search_title",
               new=AsyncMock(side_effect=AssertionError("поиск не должен дёргаться"))):
        await text_handler(_Update(), context=None)

    pipeline.assert_awaited_once()


# ── комментарии к Reels ──────────────────────────────────────────────────────


def test_fetch_top_comments_sorts_by_likes(monkeypatch):
    from backend.services import instagram_reader as ir

    items = [
        {"text": "красивый клип", "likesCount": 2},
        {"text": "Это «Девушка с жемчужной серёжкой»!", "likesCount": 240},
        {"text": "🔥🔥🔥", "likesCount": 15},
        {"text": "", "likesCount": 999},          # пустые отбрасываем
        {"error": "no_items"},                     # error-записи отбрасываем
    ]
    monkeypatch.setattr(ir, "_run_apify_actor_items", lambda *a, **k: items)

    text = ir.fetch_top_comments("https://instagram.com/reel/abc/")
    lines = text.splitlines()
    assert lines[0].startswith("- Это «Девушка с жемчужной серёжкой»!")
    assert "(240 likes)" in lines[0]
    assert len(lines) == 3


def test_fetch_top_comments_swallows_apify_errors(monkeypatch):
    from backend.services import instagram_reader as ir

    def _boom(*a, **k):
        raise ir.InstagramReaderError("down")

    monkeypatch.setattr(ir, "_run_apify_actor_items", _boom)
    assert ir.fetch_top_comments("https://instagram.com/reel/abc/") == ""
