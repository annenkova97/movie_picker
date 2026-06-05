"""Unit tests for ``search_with_fallbacks`` — the multi-source title resolver.

Focus on the behaviour that fixes series in Reels: when OMDB can't find a
title as a movie, the TMDb (movies + series) stage rescues it; and known
movies still short-circuit on the cheap OMDB path before TMDb is touched.
No network — the OMDB/TMDb singletons are patched with async stubs.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.models.movie import OMDBSearchResult
from backend.services import movie_resolver as mr
from backend.services.omdb import omdb_service
from backend.services.tmdb import tmdb_service


def _result(imdb_id: str, *, poster: bool = True) -> OMDBSearchResult:
    return OMDBSearchResult(
        imdb_id=imdb_id,
        title="Title",
        year="2026",
        poster_url="http://img/p.jpg" if poster else None,
    )


@pytest.fixture
def stub_services(monkeypatch):
    """Default everything to 'found nothing'; tests override per-stage."""
    omdb_search = AsyncMock(return_value=[])
    omdb_exact = AsyncMock(return_value=None)
    tmdb_any = AsyncMock(return_value=[])
    monkeypatch.setattr(omdb_service, "search_movies", omdb_search)
    monkeypatch.setattr(omdb_service, "get_movie_by_title", omdb_exact)
    monkeypatch.setattr(tmdb_service, "search_any", tmdb_any)
    return omdb_search, omdb_exact, tmdb_any


async def test_series_rescued_by_tmdb_stage(stub_services):
    """OMDB finds nothing as a movie; TMDb (series) resolves it."""
    omdb_search, omdb_exact, tmdb_any = stub_services
    tmdb_any.return_value = [_result("tt32937780")]

    results = await mr.search_with_fallbacks(
        "Something Very Bad Is Going to Happen",
        "У меня очень плохое предчувствие",
        seen_ids=set(),
    )

    assert [r.imdb_id for r in results] == ["tt32937780"]
    # TMDb stage (2) resolved it → OMDB exact-title (stage 4) never runs.
    tmdb_any.assert_awaited()
    omdb_exact.assert_not_awaited()


async def test_known_movie_short_circuits_before_tmdb(stub_services):
    """A clean OMDB movie hit must not spend TMDb follow-up calls."""
    omdb_search, _omdb_exact, tmdb_any = stub_services
    omdb_search.return_value = [_result("tt1375666")]  # Inception

    results = await mr.search_with_fallbacks("Inception", "Начало", seen_ids=set())

    assert [r.imdb_id for r in results] == ["tt1375666"]
    tmdb_any.assert_not_awaited()


async def test_require_poster_controls_posterless_hits(stub_services):
    """A poster-less OMDB hit is kept only when require_poster=False."""
    omdb_search, _e, _t = stub_services
    omdb_search.return_value = [_result("tt0000001", poster=False)]

    strict = await mr.search_with_fallbacks("X", "Икс", seen_ids=set())
    assert strict == []  # dropped: no poster

    loose = await mr.search_with_fallbacks(
        "X", "Икс", seen_ids=set(), require_poster=False,
    )
    assert [r.imdb_id for r in loose] == ["tt0000001"]


async def test_seen_ids_dedupes_across_calls(stub_services):
    """The shared seen_ids set prevents the same id twice across titles."""
    omdb_search, _e, _t = stub_services
    omdb_search.return_value = [_result("tt777")]
    seen: set[str] = set()

    first = await mr.search_with_fallbacks("A", "А", seen_ids=seen)
    second = await mr.search_with_fallbacks("B", "Б", seen_ids=seen)

    assert [r.imdb_id for r in first] == ["tt777"]
    assert second == []  # already seen
