"""Books CRUD + recommend integration tests.

Mirrors test_auth_and_movies for the books feature. Open Library and the LLM
are stubbed so nothing hits the network.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.models.book import BookBase, BookSearchResult


BOOK = BookBase(
    work_key="OL45804W",
    title="The Hobbit",
    authors=["J. R. R. Tolkien"],
    year=1937,
    subjects=["Fantasy", "Adventure"],
    description="A hobbit is swept into a quest to reclaim a treasure.",
    cover_url="https://covers.openlibrary.org/b/id/1-L.jpg",
    rating=None,
)

SEARCH_HIT = BookSearchResult(
    work_key="OL45804W", title="The Hobbit", author="J. R. R. Tolkien",
    year="1937", cover_url=None,
)


async def _register(client, email: str, name: str = "Reader") -> str:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "test-passw0rd-X", "name": name},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _patch_openlibrary(search=None, by_key=BOOK):
    """Patch both Open Library calls used by the books router."""
    return (
        patch(
            "backend.routers.books.openlibrary_service.get_book_by_key",
            new=AsyncMock(return_value=by_key),
        ),
        patch(
            "backend.routers.books.openlibrary_service.search_books",
            new=AsyncMock(return_value=search if search is not None else [SEARCH_HIT]),
        ),
    )


@pytest.mark.asyncio
async def test_book_lifecycle_add_list_read_delete(client):
    token = await _register(client, "books1@example.com")
    headers = _auth(token)

    p_key, p_search = _patch_openlibrary()
    with p_key, p_search:
        r = await client.post("/api/books", json={"query": "hobbit"}, headers=headers)
    assert r.status_code == 200, r.text
    book = r.json()
    assert book["work_key"] == "OL45804W"
    assert book["title"] == "The Hobbit"
    assert book["is_read"] is False
    assert book["authors"] == ["J. R. R. Tolkien"]
    book_id = book["id"]

    # Library now has exactly one book.
    r = await client.get("/api/books", headers=headers)
    assert r.status_code == 200
    assert [b["work_key"] for b in r.json()] == ["OL45804W"]

    # Mark as read.
    r = await client.patch(f"/api/books/{book_id}", json={"is_read": True}, headers=headers)
    assert r.status_code == 200
    assert r.json()["is_read"] is True

    r = await client.get("/api/books?is_read=true", headers=headers)
    assert len(r.json()) == 1

    # Delete.
    r = await client.delete(f"/api/books/{book_id}", headers=headers)
    assert r.status_code == 200
    r = await client.get("/api/books", headers=headers)
    assert r.json() == []


@pytest.mark.asyncio
async def test_add_book_by_work_key_and_dedupe(client):
    token = await _register(client, "books2@example.com")
    headers = _auth(token)

    p_key, p_search = _patch_openlibrary()
    with p_key, p_search:
        r1 = await client.post("/api/books", json={"query": "OL45804W"}, headers=headers)
        assert r1.status_code == 200
        # Adding the same work again is rejected as a duplicate.
        r2 = await client.post("/api/books", json={"query": "OL45804W"}, headers=headers)
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_book_preview_does_not_save(client):
    token = await _register(client, "books3@example.com")
    headers = _auth(token)

    p_key, p_search = _patch_openlibrary()
    with p_key, p_search:
        r = await client.get("/api/books/preview/OL45804W", headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "The Hobbit"
    # Nothing persisted by a preview.
    r = await client.get("/api/books", headers=headers)
    assert r.json() == []


@pytest.mark.asyncio
async def test_books_are_per_user(client):
    token_a = await _register(client, "books_a@example.com")
    token_b = await _register(client, "books_b@example.com")

    p_key, p_search = _patch_openlibrary()
    with p_key, p_search:
        await client.post("/api/books", json={"query": "hobbit"}, headers=_auth(token_a))

    r = await client.get("/api/books", headers=_auth(token_b))
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_book_recommend_uses_library(client):
    token = await _register(client, "books_rec@example.com")
    headers = _auth(token)

    p_key, p_search = _patch_openlibrary()
    with p_key, p_search:
        added = (await client.post("/api/books", json={"query": "hobbit"}, headers=headers)).json()

    async def _fake_recommend(query, books, max_recommendations=3):
        # Confirms (query, books) order and returns the only candidate.
        assert query == "что-нибудь волшебное"
        return ([books[0].id], "stub") if books else ([], "none")

    with patch(
        "backend.routers.books.llm_service.recommend_books",
        side_effect=_fake_recommend,
    ):
        r = await client.post(
            "/api/books/recommend",
            json={"query": "что-нибудь волшебное"},
            headers=headers,
        )
    assert r.status_code == 200
    body = r.json()
    assert [b["id"] for b in body["books"]] == [added["id"]]
