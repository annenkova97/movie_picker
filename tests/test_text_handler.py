"""Tests for the shared title-search helper (TMDB → OMDB → LLM-translate fallback)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.models.movie import OMDBSearchResult
from backend.services.title_search import find_movie_by_query, search_title


def _result(title: str, imdb_id: str = "tt0000001") -> OMDBSearchResult:
    return OMDBSearchResult(
        imdb_id=imdb_id, title=title, year="2010", poster_url=None,
    )


# ── search_title ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_title_uses_direct_omdb_hit_for_english():
    """English title that OMDB knows — no TMDB, no LLM."""
    with patch(
        "backend.services.title_search.omdb_service.search_movies",
        new=AsyncMock(return_value=[_result("Inception")]),
    ) as omdb_mock, patch(
        "backend.services.title_search.tmdb_service.api_key", new="",
    ), patch(
        "backend.services.title_search.llm_service.translate_movie_title",
        new=AsyncMock(),
    ) as translate_mock:
        results = await search_title("Inception")

    assert [r.title for r in results] == ["Inception"]
    omdb_mock.assert_awaited_once_with("Inception")
    translate_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_title_prefers_tmdb_for_cyrillic_when_enabled():
    """Cyrillic + TMDB ключ есть → TMDB первый. OMDB и LLM не дёргаются."""
    tmdb_mock = AsyncMock(return_value=[_result("Бойцовский клуб", "tt0137523")])
    omdb_mock = AsyncMock(return_value=[])
    translate_mock = AsyncMock()

    with patch("backend.services.title_search.tmdb_service.api_key", new="dummy"), \
         patch("backend.services.title_search.tmdb_service.search_any", new=tmdb_mock), \
         patch("backend.services.title_search.omdb_service.search_movies", new=omdb_mock), \
         patch("backend.services.title_search.llm_service.translate_movie_title", new=translate_mock):
        results = await search_title("Бойцовский клуб")

    assert [r.title for r in results] == ["Бойцовский клуб"]
    tmdb_mock.assert_awaited_once_with("Бойцовский клуб")
    omdb_mock.assert_not_awaited()
    translate_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_title_falls_back_to_llm_translate_when_no_tmdb():
    """Нет TMDB ключа + кириллица + OMDB не нашёл → LLM переводит → OMDB retry."""
    omdb_mock = AsyncMock(side_effect=[[], [_result("Fight Club")]])
    translate_mock = AsyncMock(return_value="Fight Club")

    with patch("backend.services.title_search.tmdb_service.api_key", new=""), \
         patch("backend.services.title_search.omdb_service.search_movies", new=omdb_mock), \
         patch("backend.services.title_search.llm_service.translate_movie_title", new=translate_mock):
        results = await search_title("Бойцовский клуб")

    assert [r.title for r in results] == ["Fight Club"]
    assert omdb_mock.await_count == 2
    omdb_mock.assert_any_await("Бойцовский клуб")
    omdb_mock.assert_any_await("Fight Club")
    translate_mock.assert_awaited_once_with("Бойцовский клуб")


@pytest.mark.asyncio
async def test_search_title_skips_translation_for_english_misses():
    """No cyrillic and no OMDB hit → не тратим LLM-вызов."""
    omdb_mock = AsyncMock(return_value=[])
    translate_mock = AsyncMock(return_value="ignored")

    with patch("backend.services.title_search.tmdb_service.api_key", new=""), \
         patch("backend.services.title_search.omdb_service.search_movies", new=omdb_mock), \
         patch("backend.services.title_search.llm_service.translate_movie_title", new=translate_mock):
        results = await search_title("something lighthearted")

    assert results == []
    translate_mock.assert_not_awaited()
    omdb_mock.assert_awaited_once_with("something lighthearted")


@pytest.mark.asyncio
async def test_search_title_handles_translate_failure_gracefully():
    """Если LLM падает — глушим и возвращаем [] вместо проброса исключения."""
    omdb_mock = AsyncMock(return_value=[])
    translate_mock = AsyncMock(side_effect=RuntimeError("API down"))

    with patch("backend.services.title_search.tmdb_service.api_key", new=""), \
         patch("backend.services.title_search.omdb_service.search_movies", new=omdb_mock), \
         patch("backend.services.title_search.llm_service.translate_movie_title", new=translate_mock):
        results = await search_title("Крестный отец")

    assert results == []


@pytest.mark.asyncio
async def test_search_title_tmdb_empty_falls_through_to_omdb():
    """TMDB включён, но ничего не нашёл → OMDB на исходном тексте → LLM."""
    tmdb_mock = AsyncMock(return_value=[])
    omdb_mock = AsyncMock(side_effect=[[], [_result("Some Movie")]])
    translate_mock = AsyncMock(return_value="Some Movie")

    with patch("backend.services.title_search.tmdb_service.api_key", new="dummy"), \
         patch("backend.services.title_search.tmdb_service.search_any", new=tmdb_mock), \
         patch("backend.services.title_search.omdb_service.search_movies", new=omdb_mock), \
         patch("backend.services.title_search.llm_service.translate_movie_title", new=translate_mock):
        results = await search_title("Какой-то редкий фильм")

    assert [r.title for r in results] == ["Some Movie"]
    tmdb_mock.assert_awaited_once()
    assert omdb_mock.await_count == 2
    translate_mock.assert_awaited_once()


# ── find_movie_by_query (для /add) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_find_by_query_imdb_id_short_circuits():
    """tt-id идёт прямиком в OMDB.get_movie_by_id, минуя поиск."""
    get_by_id = AsyncMock(return_value="MOVIE_OBJECT")

    with patch("backend.services.title_search.omdb_service.get_movie_by_id", new=get_by_id):
        result = await find_movie_by_query("tt0137523")

    assert result == "MOVIE_OBJECT"
    get_by_id.assert_awaited_once_with("tt0137523")


@pytest.mark.asyncio
async def test_find_by_query_uses_exact_match_for_english():
    """Для английского названия достаточно точного OMDB-match'а — не дёргаем поиск."""
    by_title = AsyncMock(return_value="EN_MOVIE")

    with patch("backend.services.title_search.omdb_service.get_movie_by_title", new=by_title):
        result = await find_movie_by_query("Inception")

    assert result == "EN_MOVIE"
    by_title.assert_awaited_once_with("Inception")


@pytest.mark.asyncio
async def test_find_by_query_falls_through_to_search_for_cyrillic():
    """Кириллица + exact match пустой → search_title → docrypted-id → get_by_id."""
    by_title = AsyncMock(return_value=None)
    get_by_id = AsyncMock(return_value="FULL_OMDB")
    tmdb_mock = AsyncMock(return_value=[_result("Бойцовский клуб", "tt0137523")])

    with patch("backend.services.title_search.omdb_service.get_movie_by_title", new=by_title), \
         patch("backend.services.title_search.omdb_service.get_movie_by_id", new=get_by_id), \
         patch("backend.services.title_search.tmdb_service.api_key", new="dummy"), \
         patch("backend.services.title_search.tmdb_service.search_any", new=tmdb_mock):
        result = await find_movie_by_query("Бойцовский клуб")

    assert result == "FULL_OMDB"
    get_by_id.assert_awaited_once_with("tt0137523")
