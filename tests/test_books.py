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
    """Google и Wikidata пусты → используется Open Library (последний фолбэк)."""
    from backend.services import book_search

    with patch(
        "backend.services.book_search.googlebooks_service.search_books",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.services.book_search.wikidata_service.search_books",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.services.book_search.openlibrary_service.search_books",
        new=AsyncMock(return_value=[SEARCH_HIT]),
    ) as ol:
        results = await book_search.search_books("hobbit")

    assert [r.work_key for r in results] == ["OL45804W"]
    ol.assert_called_once()


@pytest.mark.asyncio
async def test_dispatcher_uses_wikidata_before_open_library():
    """Google пуст → Wikidata подхватывает русскую книгу, до OL не доходит."""
    from backend.services import book_search

    wd_hit = BookSearchResult(
        work_key="wd:Q161885", title="Часть речи", author="Иосиф Бродский",
        year="1977", cover_url=None,
    )
    with patch(
        "backend.services.book_search.googlebooks_service.search_books",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.services.book_search.wikidata_service.search_books",
        new=AsyncMock(return_value=[wd_hit]),
    ) as wd, patch(
        "backend.services.book_search.openlibrary_service.search_books",
        new=AsyncMock(return_value=[SEARCH_HIT]),
    ) as ol:
        results = await book_search.search_books("Бродский")

    assert [r.work_key for r in results] == ["wd:Q161885"]
    wd.assert_called_once()
    ol.assert_not_called()


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
async def test_search_books_reranks_best_title_on_top():
    """Лучшее совпадение по названию всплывает над учебником/пересказом."""
    from backend.services import book_search

    hits = [
        BookSearchResult(work_key="gb:guide", title="Краткий пересказ: Война и мир",
                         author="Разбор", year=None, cover_url=None),
        BookSearchResult(work_key="gb:real", title="Война и мир",
                         author="Лев Толстой", year="1869", cover_url=None),
    ]
    with patch(
        "backend.services.book_search.googlebooks_service.search_books",
        new=AsyncMock(return_value=hits),
    ):
        results = await book_search.search_books("Война и мир")

    assert results[0].work_key == "gb:real"  # точное название — первым


@pytest.mark.asyncio
async def test_author_query_ranks_authors_works_above_books_about_them():
    """Запрос-автор «Бродский»: его произведения выше книг, ОЗАГЛАВЛЕННЫХ им.

    Регрессия на жалобу: поиск возвращал книги *про* Бродского (в названии
    «Бродский», автор — Штерн/Ахапкин) выше его собственных произведений."""
    from backend.services import book_search

    # Источник (Open Library) отдаёт вперемешку, его произведение — в середине.
    hits = [
        BookSearchResult(work_key="OL1W", title="Бродский",
                         author="Людмила Штерн", year="2023", cover_url=None),
        BookSearchResult(work_key="OL2W", title="Урания",
                         author="Иосиф Бродский", year="1987", cover_url=None),
        BookSearchResult(work_key="OL3W", title="Иосиф Бродский и Анна Ахматова",
                         author="Денис Ахапкин", year="2021", cover_url=None),
    ]
    with patch(
        "backend.services.book_search.googlebooks_service.search_books",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.services.book_search.wikidata_service.search_books",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.services.book_search.openlibrary_service.search_books",
        new=AsyncMock(return_value=hits),
    ):
        results = await book_search.search_books("Бродский")

    keys = [r.work_key for r in results]
    assert keys[0] == "OL2W"  # произведение Бродского — первым
    assert keys.index("OL2W") < keys.index("OL1W")  # выше книги «Бродский» (Штерн)
    assert keys.index("OL2W") < keys.index("OL3W")  # выше книги о нём (Ахапкин)


@pytest.mark.asyncio
async def test_google_inauthor_supplements_recall_for_author_query():
    """Для запроса-автора подмешиваются книги inauthor и встают первыми.

    Обычный запрос вернул лишь книгу *про* автора; inauthor достаёт его
    собственное произведение, и оно оказывается выше."""
    from backend.services import book_search

    work = BookSearchResult(work_key="gb:work", title="Часть речи",
                            author="Иосиф Бродский", year="1977", cover_url=None)
    about = BookSearchResult(work_key="gb:about", title="Бродский",
                             author="Людмила Штерн", year="2023", cover_url=None)

    async def _gb(q, prefer_lang=None):
        return [work] if q.startswith("inauthor:") else [about]

    with patch(
        "backend.services.book_search.googlebooks_service.search_books", new=_gb,
    ):
        results = await book_search.search_books("Бродский")

    keys = [r.work_key for r in results]
    assert keys[0] == "gb:work"     # его произведение (inauthor) — первым
    assert "gb:about" in keys       # книга про него тоже в выдаче, но ниже


@pytest.mark.asyncio
async def test_search_books_intitle_fallback_when_plain_empty():
    """Пустой обычный запрос → строгий intitle до отката на Open Library."""
    from backend.services import book_search

    calls: list[str] = []

    async def _gb(q, prefer_lang=None):
        calls.append(q)
        if q.startswith("intitle:"):
            return [BookSearchResult(work_key="gb:x", title="Редкая книга",
                                     author=None, year=None, cover_url=None)]
        return []

    with patch(
        "backend.services.book_search.googlebooks_service.search_books", new=_gb,
    ), patch(
        "backend.services.book_search.openlibrary_service.search_books",
        new=AsyncMock(return_value=[]),
    ) as ol:
        results = await book_search.search_books("Редкая книга")

    assert [r.work_key for r in results] == ["gb:x"]
    assert any(c.startswith("intitle:") for c in calls)
    ol.assert_not_called()


@pytest.mark.asyncio
async def test_search_books_retries_without_langrestrict_for_cyrillic():
    """Кириллица: пустой ответ под langRestrict=ru → повтор без фильтра языка.

    Google не всем русским томам проставляет язык; под langRestrict=ru автор
    вроде «Бродский» может вернуть пусто, а тот же запрос без ограничения —
    найтись. Без этого повтора поиск ушёл бы на бесполезный по-русски OL."""
    from backend.services import book_search

    calls: list[tuple[str, object]] = []

    async def _gb(q, prefer_lang=None):
        calls.append((q, prefer_lang))
        if prefer_lang == "ru":
            return []  # под языковым фильтром — пусто
        return [BookSearchResult(work_key="gb:brodsky", title="Часть речи",
                                 author="Иосиф Бродский", year="1977", cover_url=None)]

    with patch(
        "backend.services.book_search.googlebooks_service.search_books", new=_gb,
    ), patch(
        "backend.services.book_search.openlibrary_service.search_books",
        new=AsyncMock(return_value=[]),
    ) as ol:
        results = await book_search.search_books("Бродский")

    assert [r.work_key for r in results] == ["gb:brodsky"]
    # Сначала с ru, затем тот же запрос без него; до Open Library не дошло.
    assert ("Бродский", "ru") in calls
    assert ("Бродский", None) in calls
    ol.assert_not_called()


@pytest.mark.asyncio
async def test_openlibrary_search_survives_network_error():
    """Open Library (последний фолбэк) упал → [] вместо 500 на весь /search."""
    import httpx

    from backend.services.openlibrary import openlibrary_service

    class _BoomClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): raise httpx.ConnectError("boom")

    with patch("backend.services.openlibrary.httpx.AsyncClient", _BoomClient):
        results = await openlibrary_service.search_books("Бродский")

    assert results == []


# ----- Wikidata provider (бесключевой русский фолбэк) -----


class _FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


def _fake_client(route):
    """Подменяет httpx.AsyncClient: ``route(url, params)`` → _FakeResp."""
    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None, headers=None):
            return route(url, params or {})
    return _Client


@pytest.mark.asyncio
async def test_wikidata_search_parses_sparql_and_dedupes():
    """SPARQL-выдача → BookSearchResult; пустышки (label==QID) и дубли отсеяны."""
    from backend.services.wikidata import wikidata_service

    sparql_json = {"results": {"bindings": [
        {"work": {"value": "http://www.wikidata.org/entity/Q161885"},
         "workLabel": {"value": "Часть речи"},
         "authorLabel": {"value": "Иосиф Бродский"},
         "year": {"value": "1977"},
         "image": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/cover.jpg"}},
        # дубль того же произведения (второй автор) — должен схлопнуться
        {"work": {"value": "http://www.wikidata.org/entity/Q161885"},
         "workLabel": {"value": "Часть речи"},
         "authorLabel": {"value": "Кто-то ещё"}},
        # пустышка: лейбл-сервис вернул сам QID — пропускаем
        {"work": {"value": "http://www.wikidata.org/entity/Q999"},
         "workLabel": {"value": "Q999"}},
    ]}}

    def route(url, params):
        return _FakeResp(sparql_json)

    with patch("backend.services.wikidata.httpx.AsyncClient", _fake_client(route)):
        results = await wikidata_service.search_books("Бродский")

    assert [r.work_key for r in results] == ["wd:Q161885"]
    r = results[0]
    assert r.title == "Часть речи"
    assert r.author == "Иосиф Бродский"
    assert r.year == "1977"
    assert r.cover_url and r.cover_url.startswith("https://") and "width=" in r.cover_url


@pytest.mark.asyncio
async def test_wikidata_get_book_by_key_builds_metadata():
    """wbgetentities (сущность + лейблы авторов/жанров) → BookBase."""
    from backend.services.wikidata import wikidata_service

    entity_json = {"entities": {"Q161885": {
        "labels": {"ru": {"value": "Часть речи"}},
        "descriptions": {"ru": {"value": "сборник стихотворений"}},
        "claims": {
            "P50": [{"mainsnak": {"datavalue": {"value": {"id": "Q991"}}}}],
            "P136": [{"mainsnak": {"datavalue": {"value": {"id": "Q482"}}}}],
            "P577": [{"mainsnak": {"datavalue": {"value": {"time": "+1977-00-00T00:00:00Z"}}}}],
            "P18": [{"mainsnak": {"datavalue": {"value": "cover.jpg"}}}],
        },
    }}}
    labels_json = {"entities": {
        "Q991": {"labels": {"ru": {"value": "Иосиф Бродский"}}},
        "Q482": {"labels": {"ru": {"value": "поэзия"}}},
    }}

    def route(url, params):
        ids = params.get("ids", "")
        if ids == "Q161885":
            return _FakeResp(entity_json)
        return _FakeResp(labels_json)

    with patch("backend.services.wikidata.httpx.AsyncClient", _fake_client(route)):
        book = await wikidata_service.get_book_by_key("wd:Q161885")

    assert book is not None
    assert book.work_key == "wd:Q161885"
    assert book.title == "Часть речи"
    assert book.authors == ["Иосиф Бродский"]
    assert book.year == 1977
    assert book.subjects == ["поэзия"]
    assert book.description == "сборник стихотворений"
    assert book.cover_url and "cover.jpg" in book.cover_url


@pytest.mark.asyncio
async def test_wikidata_search_survives_errors():
    """Любая ошибка Wikidata → [] (это фолбэк, он не должен ронять поиск)."""
    import httpx

    from backend.services.wikidata import wikidata_service

    class _BoomClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): raise httpx.ConnectTimeout("boom")

    with patch("backend.services.wikidata.httpx.AsyncClient", _BoomClient):
        results = await wikidata_service.search_books("Бродский")

    assert results == []


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
