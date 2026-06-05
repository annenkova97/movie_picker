"""Tests for Instagram Reel → OMDB search pipeline.

`/api/instagram/search` now requires auth (it spends Apify credits), so these
tests register a user first. The end-to-end case hits the real Apify + OpenAI
pipeline, so it is gated behind RUN_INTEGRATION=1 to keep CI hermetic.
"""

import os

import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app


async def _auth_headers(client: AsyncClient, email: str) -> dict[str, str]:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "test-passw0rd-X", "name": "IG"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


REEL_TEST_CASES = [
    {
        "url": "https://www.instagram.com/reel/DS40P4JDLfm/",
        "expected_imdb_ids": ["tt12300742"],  # Bugonia (2025)
        "description": "Reel about Bugonia by Yorgos Lanthimos with Emma Stone",
    },
]


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="hits live Apify/OpenAI; set RUN_INTEGRATION=1 to run",
)
async def test_instagram_search_returns_expected_movies():
    """Instagram reel search should find the correct movies in OMDB."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _auth_headers(client, "ig_integration@example.com")
        for case in REEL_TEST_CASES:
            response = await client.post(
                "/api/instagram/search",
                json={"url": case["url"], "vision": False},
                headers=headers,
            )
            assert response.status_code == 200, (
                f"Failed for {case['url']}: {response.text}"
            )
            found_ids = {r["imdb_id"] for r in response.json()}
            for expected_id in case["expected_imdb_ids"]:
                assert expected_id in found_ids, (
                    f"Expected {expected_id} for: {case['description']}"
                )


@pytest.mark.asyncio
async def test_instagram_search_requires_auth():
    """Unauthenticated calls are rejected before any work is done."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/instagram/search",
            json={"url": "https://www.instagram.com/reel/abc/", "vision": False},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_instagram_search_invalid_url():
    """An authenticated request with a non-Instagram URL is a 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _auth_headers(client, "ig_badurl@example.com")
        response = await client.post(
            "/api/instagram/search",
            json={"url": "https://youtube.com/watch?v=abc", "vision": False},
            headers=headers,
        )
        assert response.status_code == 400
