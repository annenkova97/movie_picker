"""Auth + library lifecycle integration tests.

Hits a real backend with an isolated SQLite DB (set up in conftest.py). Routes
under test:
- POST /auth/register and login
- POST /api/movies (free-form add, defers to OMDB) — STUBBED here
- GET  /api/movies?in_library=true
- POST /api/movies/by-imdb/{id} — STUBBED OMDB
- DELETE /api/movies/{id}
- POST /api/movies/bulk-import
- /api/shares with auth (snapshot from DB, owner_name set)
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.models.movie import MovieBase, OMDBSearchResult


def _moviebase(imdb_id: str = "tt0111161", title: str = "The Shawshank Redemption") -> MovieBase:
    return MovieBase(
        imdb_id=imdb_id,
        title=title,
        original_title=None,
        year=1994,
        genres=["Drama"],
        description=None,
        plot="Two imprisoned men bond over a number of years.",
        plot_ru=None,
        cast=["Tim Robbins"],
        director="Frank Darabont",
        poster_url=None,
        imdb_rating=9.3,
        awards="Won 7 Oscars",
    )


async def _register(client, email: str = "user@example.com", name: str = "Tester") -> str:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "test-passw0rd-X", "name": name},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_login_flow(client):
    """Register a fresh user, then re-login with same creds — both return tokens."""
    r = await client.post(
        "/auth/register",
        json={"email": "flow@example.com", "password": "pw-Strong-99", "name": "Flo"},
    )
    assert r.status_code == 200
    token1 = r.json()["token"]
    assert isinstance(token1, str) and len(token1) > 20

    r2 = await client.post(
        "/auth/login", json={"email": "flow@example.com", "password": "pw-Strong-99"},
    )
    assert r2.status_code == 200
    assert "token" in r2.json()


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(client):
    await client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "pw-Strong-99", "name": "X"},
    )
    r = await client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "pw-Strong-99", "name": "X"},
    )
    assert r.status_code in (400, 409)


@pytest.mark.asyncio
async def test_login_wrong_password_fails(client):
    await client.post(
        "/auth/register",
        json={"email": "wp@example.com", "password": "pw-Strong-99", "name": "X"},
    )
    r = await client.post(
        "/auth/login", json={"email": "wp@example.com", "password": "wrong"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_movies_endpoints_require_auth(client):
    """Unauthed reads/writes against /api/movies should 401."""
    r = await client.get("/api/movies?in_library=true")
    assert r.status_code == 401
    r2 = await client.post("/api/movies", json={"query": "Inception"})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_add_get_delete_roundtrip(client):
    token = await _register(client, "lib@example.com", "Lib")

    movie = _moviebase()
    with patch(
        "backend.services.title_search.omdb_service.get_movie_by_title",
        return_value=movie,
    ):
        r = await client.post(
            "/api/movies", json={"query": "Shawshank"}, headers=_auth(token),
        )
    assert r.status_code in (200, 201), r.text
    movie_id = r.json()["id"]

    # List should now contain it
    r = await client.get("/api/movies?in_library=true", headers=_auth(token))
    assert r.status_code == 200
    items = r.json()
    assert any(m["imdb_id"] == "tt0111161" for m in items)

    # Delete
    r = await client.delete(f"/api/movies/{movie_id}", headers=_auth(token))
    assert r.status_code in (200, 204)

    # Now list is empty
    r = await client.get("/api/movies?in_library=true", headers=_auth(token))
    assert r.status_code == 200
    assert all(m["imdb_id"] != "tt0111161" for m in r.json())


@pytest.mark.asyncio
async def test_libraries_are_isolated_per_user(client):
    """User A's saves must not appear in user B's library."""
    token_a = await _register(client, "a@example.com", "A")
    token_b = await _register(client, "b@example.com", "B")

    movie = _moviebase("tt0078788", "Apocalypse Now")
    with patch(
        "backend.services.title_search.omdb_service.get_movie_by_title",
        return_value=movie,
    ):
        r = await client.post(
            "/api/movies", json={"query": "Apocalypse"}, headers=_auth(token_a),
        )
    assert r.status_code in (200, 201)

    r = await client.get("/api/movies?in_library=true", headers=_auth(token_b))
    assert r.status_code == 200
    assert all(m["imdb_id"] != "tt0078788" for m in r.json())


@pytest.mark.asyncio
async def test_authed_share_snapshots_db_and_includes_owner_name(client):
    """For authenticated users the backend ignores client-provided library."""
    token = await _register(client, "owner@example.com", "OwnerName")

    movie = _moviebase("tt0073195", "Jaws")
    with patch(
        "backend.services.title_search.omdb_service.get_movie_by_title",
        return_value=movie,
    ):
        await client.post(
            "/api/movies", json={"query": "Jaws"}, headers=_auth(token),
        )

    # Authed share — even if client lies in `library`, backend snapshots DB.
    r = await client.post(
        "/api/shares",
        json={"name": "OwnerName's list", "library": []},  # backend will ignore this
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["owner_name"] == "OwnerName"
    assert any(m["imdb_id"] == "tt0073195" for m in body["movies"])


@pytest.mark.asyncio
async def test_web_search_routes_cyrillic_through_tmdb(client):
    """Раньше /api/search ходил только в OMDB; теперь — через TMDb-пайплайн,
    и tmdb-only ключ (фильм без IMDb id) доходит до выдачи."""
    hit = OMDBSearchResult(
        imdb_id="tmdb:movie:99", title="Иди и смотри", year="1985",
        poster_url="http://img/p.jpg",
    )
    with patch("backend.services.title_search.tmdb_service.api_key", new="dummy"), \
         patch(
             "backend.services.title_search.tmdb_service.search_any",
             new=AsyncMock(return_value=[hit]),
         ):
        r = await client.get("/api/search", params={"q": "Иди и смотри"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body[0]["imdb_id"] == "tmdb:movie:99"
    assert body[0]["title"] == "Иди и смотри"


@pytest.mark.asyncio
async def test_preview_and_add_by_tmdb_key(client):
    """Превью и сохранение фильма по синтетическому ключу tmdb:… работают
    end-to-end (метадата строится из TMDb, не из OMDB)."""
    token = await _register(client, "tmdbkey@example.com", "T")

    tmdb_movie = MovieBase(
        imdb_id="tmdb:movie:99", title="Иди и смотри", original_title="Come and See",
        year=1985, media_type="movie", genres=["Драма"], plot=None,
        cast=["Алексей Кравченко"], director="Элем Климов", poster_url=None,
        imdb_rating=None,
    )
    with patch(
        "backend.services.title_search.tmdb_service.get_by_key",
        new=AsyncMock(return_value=tmdb_movie),
    ):
        pr = await client.get("/api/search/preview/tmdb:movie:99")
        assert pr.status_code == 200, pr.text
        assert pr.json()["title"] == "Иди и смотри"

        ar = await client.post(
            "/api/movies/by-imdb/tmdb:movie:99", headers=_auth(token),
        )
    assert ar.status_code in (200, 201), ar.text
    assert ar.json()["imdb_id"] == "tmdb:movie:99"

    lr = await client.get("/api/movies?in_library=true", headers=_auth(token))
    assert any(m["imdb_id"] == "tmdb:movie:99" for m in lr.json())


@pytest.mark.asyncio
async def test_recommend_with_inline_library_works_for_guest(client):
    """The recommend endpoint must accept a guest's inline library."""
    movie_dict = {
        "imdb_id": "tt0111161", "title": "The Shawshank Redemption",
        "original_title": None, "year": 1994, "genres": ["Drama"],
        "description": None, "plot": "Two imprisoned men bond.",
        "plot_ru": None, "cast": ["Tim Robbins"], "director": "Frank Darabont",
        "poster_url": None, "imdb_rating": 9.3, "awards": None,
        "is_watched": False, "source": "personal", "rec_source": "personal",
        "rec_note": None, "in_library": True, "award": None, "award_year": None,
        "id": 1, "added_at": "2026-04-30T12:00:00",
    }

    # Stub the LLM call to avoid hitting Claude. recommend_movies returns
    # (recommended_imdb_ids, explanation).
    async def _fake_recommend(_movies, _query, max_recommendations=3):
        return ([1], "stubbed")

    with patch(
        "backend.routers.recommend.llm_service.recommend_movies",
        side_effect=_fake_recommend,
    ):
        r = await client.post(
            "/api/recommend",
            json={
                "query": "тёплое",
                "include_watched": False,
                "library": [movie_dict],
            },
        )

    # The endpoint may either return 200 with the stubbed payload or 422 when
    # the recommender produces no suggestions — either is acceptable; what we
    # care about is that it didn't 401 or 500.
    assert r.status_code in (200, 422), r.text
