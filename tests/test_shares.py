"""Integration tests for /api/shares — guest creation and read flow."""

from __future__ import annotations

from typing import Any

import pytest


def _sample_movie(imdb_id: str = "tt0111161", title: str = "The Shawshank Redemption") -> dict[str, Any]:
    return {
        "id": 1,
        "imdb_id": imdb_id,
        "title": title,
        "original_title": None,
        "year": 1994,
        "genres": ["Drama"],
        "description": None,
        "plot": "Two imprisoned men bond over a number of years.",
        "plot_ru": None,
        "cast": ["Tim Robbins"],
        "director": "Frank Darabont",
        "poster_url": None,
        "imdb_rating": 9.3,
        "awards": "Won 7 Oscars",
        "is_watched": False,
        "source": "personal",
        "rec_source": "personal",
        "rec_note": None,
        "in_library": True,
        "award": None,
        "award_year": None,
        "added_at": "2026-04-30T12:00:00",
    }


@pytest.mark.asyncio
async def test_guest_can_create_and_read_share(client):
    """Guest with inline library: POST creates a share, GET reads it back."""
    movie = _sample_movie()
    r = await client.post(
        "/api/shares",
        json={"name": "Nastya's list", "library": [movie]},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    slug = data["slug"]
    assert isinstance(slug, str) and len(slug) >= 4
    assert data["name"] == "Nastya's list"
    assert data["owner_name"] is None  # guest -> no owner
    assert len(data["movies"]) == 1
    assert data["movies"][0]["imdb_id"] == "tt0111161"

    # GET roundtrip
    r2 = await client.get(f"/api/shares/{slug}")
    assert r2.status_code == 200
    got = r2.json()
    assert got["slug"] == slug
    assert got["name"] == "Nastya's list"
    assert len(got["movies"]) == 1
    assert got["movies"][0]["title"] == "The Shawshank Redemption"


@pytest.mark.asyncio
async def test_create_rejects_empty_name(client):
    r = await client.post(
        "/api/shares",
        json={"name": "   ", "library": [_sample_movie()]},
    )
    assert r.status_code == 422
    assert "name" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_rejects_empty_library_for_guest(client):
    r = await client.post("/api/shares", json={"name": "x", "library": []})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_missing_library_for_guest(client):
    # Guest path: no auth, no library — backend can't snapshot anything.
    r = await client.post("/api/shares", json={"name": "x"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_missing_slug_returns_404(client):
    r = await client.get("/api/shares/no_such_slug_xyz_999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_long_name_is_truncated(client):
    long_name = "n" * 1000
    r = await client.post(
        "/api/shares",
        json={"name": long_name, "library": [_sample_movie()]},
    )
    assert r.status_code == 200
    # Backend caps to MAX_NAME_LENGTH (80).
    assert len(r.json()["name"]) <= 80


@pytest.mark.asyncio
async def test_two_shares_get_distinct_slugs(client):
    r1 = await client.post(
        "/api/shares", json={"name": "A", "library": [_sample_movie()]},
    )
    r2 = await client.post(
        "/api/shares", json={"name": "B", "library": [_sample_movie()]},
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["slug"] != r2.json()["slug"]
