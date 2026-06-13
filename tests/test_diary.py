"""Дневник: личная оценка (1–5), заметка и авто-дата просмотра/прочтения.

Покрывает фильмы и книги (PATCH user_rating/user_note), автопроставление
watched_at/read_at при отметке, очистку оценки нулём, валидацию диапазона и
то, что личная заметка НЕ утекает в публичный шэр (а оценка — остаётся).

OMDB и Open Library застаблены — сеть не дёргается. DB — изолированный SQLite
из conftest.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.models.book import BookBase, BookSearchResult
from backend.models.movie import MovieBase


def _moviebase(imdb_id: str = "tt0111161", title: str = "The Shawshank Redemption") -> MovieBase:
    return MovieBase(
        imdb_id=imdb_id, title=title, year=1994, genres=["Drama"],
        plot="Two imprisoned men bond over a number of years.",
        cast=["Tim Robbins"], director="Frank Darabont", imdb_rating=9.3,
    )


_BOOK = BookBase(
    work_key="OL45804W", title="The Hobbit", authors=["J. R. R. Tolkien"],
    year=1937, subjects=["Fantasy"], description="A quest.", cover_url=None, rating=None,
)
_SEARCH_HIT = BookSearchResult(
    work_key="OL45804W", title="The Hobbit", author="J. R. R. Tolkien",
    year="1937", cover_url=None,
)


async def _register(client, email: str, name: str = "Diarist") -> str:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "test-passw0rd-X", "name": name},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _add_movie(client, headers, imdb_id="tt0111161") -> dict:
    with patch(
        "backend.services.title_search.omdb_service.get_movie_by_title",
        return_value=_moviebase(imdb_id),
    ):
        r = await client.post("/api/movies", json={"query": "Shawshank"}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def _add_book(client, headers) -> dict:
    p_key = patch(
        "backend.routers.books.book_search.get_book_by_key",
        new=AsyncMock(return_value=_BOOK),
    )
    p_search = patch(
        "backend.routers.books.book_search.search_books",
        new=AsyncMock(return_value=[_SEARCH_HIT]),
    )
    with p_key, p_search:
        r = await client.post("/api/books", json={"query": "hobbit"}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ── movies ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_movie_rating_and_note_persist(client):
    headers = _auth(await _register(client, "diary_m1@example.com"))
    movie = await _add_movie(client, headers)

    r = await client.patch(
        f"/api/movies/{movie['id']}",
        json={"is_watched": True, "user_rating": 5, "user_note": "Тот самый финал"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_rating"] == 5
    assert body["user_note"] == "Тот самый финал"
    # Дата просмотра проставилась автоматически.
    assert body["watched_at"] is not None

    # Значения переживают перечитывание.
    r = await client.get(f"/api/movies/{movie['id']}", headers=headers)
    assert r.json()["user_rating"] == 5
    assert r.json()["user_note"] == "Тот самый финал"


@pytest.mark.asyncio
async def test_watched_at_set_once_not_overwritten(client):
    headers = _auth(await _register(client, "diary_m2@example.com"))
    movie = await _add_movie(client, headers, imdb_id="tt0068646")

    r1 = await client.patch(
        f"/api/movies/{movie['id']}", json={"is_watched": True}, headers=headers,
    )
    first = r1.json()["watched_at"]
    assert first is not None

    # Повторная отметка просмотренным не должна перетереть дату первого просмотра.
    r2 = await client.patch(
        f"/api/movies/{movie['id']}",
        json={"is_watched": True, "user_rating": 4},
        headers=headers,
    )
    assert r2.json()["watched_at"] == first


@pytest.mark.asyncio
async def test_rating_zero_clears(client):
    headers = _auth(await _register(client, "diary_m3@example.com"))
    movie = await _add_movie(client, headers, imdb_id="tt0468569")

    await client.patch(
        f"/api/movies/{movie['id']}", json={"user_rating": 3}, headers=headers,
    )
    r = await client.patch(
        f"/api/movies/{movie['id']}", json={"user_rating": 0}, headers=headers,
    )
    assert r.json()["user_rating"] is None


@pytest.mark.asyncio
async def test_rating_out_of_range_rejected(client):
    headers = _auth(await _register(client, "diary_m4@example.com"))
    movie = await _add_movie(client, headers, imdb_id="tt1375666")

    r = await client.patch(
        f"/api/movies/{movie['id']}", json={"user_rating": 9}, headers=headers,
    )
    assert r.status_code == 422


# ── books ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_book_rating_note_and_read_at(client):
    headers = _auth(await _register(client, "diary_b1@example.com"))
    book = await _add_book(client, headers)

    r = await client.patch(
        f"/api/books/{book['id']}",
        json={"is_read": True, "user_rating": 4, "user_note": "Перечитать зимой"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_rating"] == 4
    assert body["user_note"] == "Перечитать зимой"
    assert body["read_at"] is not None


# ── privacy: personal note must not leak into a public share ──────────────────


@pytest.mark.asyncio
async def test_share_strips_user_note_keeps_rating(client):
    headers = _auth(await _register(client, "diary_share@example.com", "Sharer"))
    movie = await _add_movie(client, headers, imdb_id="tt0073195")
    await client.patch(
        f"/api/movies/{movie['id']}",
        json={"is_watched": True, "user_rating": 5, "user_note": "СЕКРЕТ"},
        headers=headers,
    )

    created = await client.post(
        "/api/shares", json={"name": "My picks", "library": []}, headers=headers,
    )
    assert created.status_code == 200, created.text
    slug = created.json()["slug"]

    # Публичное чтение шэра: заметки нет, оценка есть.
    public = await client.get(f"/api/shares/{slug}")
    assert public.status_code == 200
    shared_movie = next(
        m for m in public.json()["movies"] if m["imdb_id"] == "tt0073195"
    )
    assert shared_movie.get("user_note") is None
    assert shared_movie["user_rating"] == 5
