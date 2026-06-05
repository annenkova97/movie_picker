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
    """Patch the book-search dispatcher used by the books router.

    (Named for history; the router now goes through ``book_search`` which
    fronts Google Books + Open Library.)
    """
    return (
        patch(
            "backend.routers.books.book_search.get_book_by_key",
            new=AsyncMock(return_value=by_key),
        ),
        patch(
            "backend.routers.books.book_search.search_books",
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
async def test_dispatcher_prefers_google_books(client):
    """book_search returns Google Books hits without touching Open Library."""
    from backend.services import book_search

    gb_hit = BookSearchResult(
        work_key="gb:abc123", title="Часть речи", author="Иосиф Бродский",
        year="1977", cover_url=None,
    )
    with patch(
        "backend.services.book_search.googlebooks_service.search_books",
        new=AsyncMock(return_value=[gb_hit]),
    ) as gb, patch(
        "backend.services.book_search.openlibrary_service.search_books",
        new=AsyncMock(return_value=[SEARCH_HIT]),
    ) as ol:
        results = await book_search.search_books("Бродский")

    assert [r.work_key for r in results] == ["gb:abc123"]
    # Кириллица → langRestrict=ru, и Open Library не дёргался.
    assert gb.call_args.kwargs.get("prefer_lang") == "ru"
    ol.assert_not_called()


@pytest.mark.asyncio
async def test_dispatcher_falls_back_to_open_library(client):
    """When Google Books returns nothing, Open Library is used."""
    from backend.services import book_search

    with patch(
        "backend.services.book_search.googlebooks_service.search_books",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.services.book_search.openlibrary_service.search_books",
        new=AsyncMock(return_value=[SEARCH_HIT]),
    ) as ol:
        results = await book_search.search_books("hobbit")

    assert [r.work_key for r in results] == ["OL45804W"]
    ol.assert_called_once()


@pytest.mark.asyncio
async def test_get_book_by_key_dispatches_by_prefix(client):
    """gb: keys go to Google Books, OL…W keys to Open Library."""
    from backend.services import book_search

    gb_book = BookBase(work_key="gb:abc123", title="Часть речи", authors=["Иосиф Бродский"])
    with patch(
        "backend.services.book_search.googlebooks_service.get_book_by_key",
        new=AsyncMock(return_value=gb_book),
    ) as gb, patch(
        "backend.services.book_search.openlibrary_service.get_book_by_key",
        new=AsyncMock(return_value=BOOK),
    ) as ol:
        from_gb = await book_search.get_book_by_key("gb:abc123")
        from_ol = await book_search.get_book_by_key("OL45804W")

    assert from_gb.work_key == "gb:abc123"
    assert from_ol.work_key == "OL45804W"
    gb.assert_awaited_once()
    ol.assert_awaited_once()


@pytest.mark.asyncio
async def test_brodsky_search_endpoint_returns_hits(client):
    """Regression for the original complaint: «Бродский» finds books now."""
    gb_hit = BookSearchResult(
        work_key="gb:zzz", title="Стихотворения", author="Иосиф Бродский",
        year="1965", cover_url=None,
    )
    with patch(
        "backend.services.book_search.googlebooks_service.search_books",
        new=AsyncMock(return_value=[gb_hit]),
    ):
        r = await client.get("/api/books/search?q=Бродский")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["author"] == "Иосиф Бродский"


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
