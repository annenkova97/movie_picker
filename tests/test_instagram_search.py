"""Tests for Instagram Reel → OMDB search pipeline."""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app

REEL_TEST_CASES = [
    {
        "url": "https://www.instagram.com/reel/DS40P4JDLfm/",
        "expected_imdb_ids": ["tt12300742"],  # Bugonia (2025)
        "description": "Reel about Bugonia by Yorgos Lanthimos with Emma Stone",
    },
]


@pytest.mark.asyncio
async def test_instagram_search_returns_expected_movies():
    """Instagram reel search should find the correct movies in OMDB."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for case in REEL_TEST_CASES:
            response = await client.post(
                "/api/instagram/search",
                json={"url": case["url"], "vision": False},
            )

            assert response.status_code == 200, (
                f"Failed for {case['url']}: {response.text}"
            )

            results = response.json()
            found_ids = {r["imdb_id"] for r in results}

            for expected_id in case["expected_imdb_ids"]:
                assert expected_id in found_ids, (
                    f"Expected {expected_id} in results for: {case['description']}. "
                    f"Got: {[r['imdb_id'] + ' ' + r['title'] for r in results]}"
                )


@pytest.mark.asyncio
async def test_instagram_search_invalid_url():
    """Should return 400 for non-Instagram URLs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/instagram/search",
            json={"url": "https://youtube.com/watch?v=abc", "vision": False},
        )
        assert response.status_code == 400
