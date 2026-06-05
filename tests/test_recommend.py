"""Tests for the mood-based recommendation endpoint.

Focus: the award-winners catalog must be merged into the candidate pool that is
handed to the LLM (feature #4), and the merge/argument order must be correct.
The LLM and the awards DB read are both stubbed so nothing hits the network.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.models import Movie


# A guest's inline library movie (id=1).
GUEST_MOVIE = {
    "imdb_id": "tt0111161", "title": "The Shawshank Redemption",
    "original_title": None, "year": 1994, "genres": ["Drama"],
    "description": None, "plot": "Two imprisoned men bond.",
    "plot_ru": None, "cast": ["Tim Robbins"], "director": "Frank Darabont",
    "poster_url": None, "imdb_rating": 9.3, "awards": None,
    "is_watched": False, "source": "personal", "rec_source": "personal",
    "rec_note": None, "in_library": True, "award": None, "award_year": None,
    "id": 1, "added_at": "2026-04-30T12:00:00",
}

# An award-winner from the global catalog (id=999) the user has NOT saved.
AWARD = Movie(
    id=999, imdb_id="tt9999999", title="Award Winner", original_title=None,
    year=2024, genres=["Drama"], description=None, plot="An acclaimed film.",
    plot_ru=None, cast=["Someone"], director="A Director", poster_url=None,
    imdb_rating=8.5, awards="Won 1 Oscar.", is_watched=False, source="awards",
    rec_source=None, rec_note=None, in_library=False, award="Oscar Best Picture",
    award_year=2024, added_at="2024-01-01T00:00:00",
)


@pytest.mark.asyncio
async def test_recommend_merges_award_winners_into_candidate_pool(client):
    """Awards are added to the pool, and the LLM receives (query, movies)."""
    captured: dict = {}

    async def _fake_recommend(query, movies, max_recommendations=3):
        captured["query"] = query
        captured["movies"] = movies
        # Recommend the award winner so we can also assert it round-trips out.
        return ([AWARD.id], "stubbed")

    with patch(
        "backend.routers.recommend.db.get_awards",
        new=AsyncMock(return_value=[AWARD]),
    ), patch(
        "backend.routers.recommend.llm_service.recommend_movies",
        side_effect=_fake_recommend,
    ):
        r = await client.post(
            "/api/recommend",
            json={"query": "что-то сильное", "library": [GUEST_MOVIE]},
        )

    assert r.status_code == 200

    # Argument order is (query_string, movies_list) — guards the latent swap.
    assert captured["query"] == "что-то сильное"
    imdb_ids = {m.imdb_id for m in captured["movies"]}
    assert "tt0111161" in imdb_ids          # the guest's own film is kept
    assert "tt9999999" in imdb_ids          # the award winner is mixed in

    # The award winner can therefore be returned even though it was never saved.
    body = r.json()
    assert any(m["imdb_id"] == "tt9999999" for m in body["movies"])


@pytest.mark.asyncio
async def test_recommend_dedupes_award_already_in_library(client):
    """If the user already saved an award, their own copy is the only one."""
    saved_award = dict(GUEST_MOVIE)
    saved_award["imdb_id"] = AWARD.imdb_id  # same film as the catalog award
    saved_award["id"] = 7

    captured: dict = {}

    async def _fake_recommend(query, movies, max_recommendations=3):
        captured["movies"] = movies
        return ([], "stubbed")

    with patch(
        "backend.routers.recommend.db.get_awards",
        new=AsyncMock(return_value=[AWARD]),
    ), patch(
        "backend.routers.recommend.llm_service.recommend_movies",
        side_effect=_fake_recommend,
    ):
        r = await client.post(
            "/api/recommend",
            json={"query": "драма", "library": [saved_award]},
        )

    assert r.status_code == 200
    matches = [m for m in captured["movies"] if m.imdb_id == AWARD.imdb_id]
    assert len(matches) == 1            # deduped by imdb_id
    assert matches[0].id == 7           # the user's own copy won
