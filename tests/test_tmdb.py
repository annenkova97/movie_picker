"""Unit tests for the TMDb service — movie + TV search. No network.

We patch ``httpx.AsyncClient`` with a tiny fake that routes by URL, so these
exercise the real parsing/merging logic without touching TMDb.
"""

from __future__ import annotations

import pytest

import backend.services.tmdb as tmdb_mod
from backend.services.tmdb import tmdb_service


class _Resp:
    def __init__(self, data: dict) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._data


class _FakeClient:
    """Async-context httpx stand-in dispatching GETs to a handler(url, params)."""

    def __init__(self, handler) -> None:
        self._handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def get(self, url, params=None):
        return _Resp(self._handler(url, params or {}))


@pytest.fixture
def patch_tmdb(monkeypatch):
    """Install a fake httpx client + a non-empty api key (so ``enabled``)."""
    monkeypatch.setattr(tmdb_service, "api_key", "test-key")

    def _install(handler):
        monkeypatch.setattr(
            tmdb_mod.httpx, "AsyncClient",
            lambda *a, **k: _FakeClient(handler),
        )

    return _install


# ── search_tv ───────────────────────────────────────────────────────────────


def _tv_handler(url, _params):
    if "/search/tv" in url:
        return {"results": [
            {
                "id": 1,
                "name": "У меня очень плохое предчувствие",
                "original_name": "Something Very Bad Is Going to Happen",
                "first_air_date": "2026-04-01",
                "poster_path": "/poster.jpg",
            },
            {  # no external imdb_id → kept as a synthetic tmdb: key now
                "id": 2,
                "name": "Безымянный сериал",
                "first_air_date": "2020-01-01",
                "poster_path": None,
            },
        ]}
    if url.endswith("/tv/1/external_ids"):
        return {"imdb_id": "tt32937780"}
    if url.endswith("/tv/2/external_ids"):
        return {"imdb_id": ""}  # empty → no IMDb link → synthetic key
    return {}


async def test_search_tv_maps_series_fields(patch_tmdb):
    patch_tmdb(_tv_handler)

    results = await tmdb_service.search_tv("У меня очень плохое предчувствие")

    # Exact-title hit ranks first; the imdb-less one is no longer dropped but
    # carried as a synthetic tmdb: key so it stays findable.
    assert len(results) == 2
    first = results[0]
    assert first.imdb_id == "tt32937780"
    assert first.title == "У меня очень плохое предчувствие"  # name preferred
    assert first.year == "2026"  # first_air_date[:4]
    assert first.poster_url and first.poster_url.endswith("/poster.jpg")

    synthetic = results[1]
    assert synthetic.imdb_id == "tmdb:tv:2"
    assert synthetic.year == "2020"
    assert synthetic.poster_url is None


async def test_search_tv_disabled_without_key(monkeypatch, patch_tmdb):
    patch_tmdb(_tv_handler)
    monkeypatch.setattr(tmdb_service, "api_key", "")  # disable
    assert await tmdb_service.search_tv("anything") == []


async def test_search_tv_empty_query_is_noop(patch_tmdb):
    patch_tmdb(_tv_handler)
    assert await tmdb_service.search_tv("   ") == []


# ── search_any (movies + TV merged) ──────────────────────────────────────────


def _any_handler(url, _params):
    if "/search/movie" in url:
        return {"results": [
            {"id": 10, "title": "Дюна", "release_date": "2021-09-15",
             "poster_path": "/dune.jpg"},
        ]}
    if "/search/tv" in url:
        return {"results": [
            {"id": 20, "name": "Дюна: Пророчество", "first_air_date": "2024-11-17",
             "poster_path": "/dune-tv.jpg"},
            {"id": 10, "name": "Дубль фильма", "first_air_date": "2021-01-01",
             "poster_path": "/dup.jpg"},  # shares imdb tt-movie → dedup
        ]}
    if url.endswith("/movie/10"):
        return {"imdb_id": "tt-movie"}
    if url.endswith("/tv/20/external_ids"):
        return {"imdb_id": "tt-series"}
    if url.endswith("/tv/10/external_ids"):
        return {"imdb_id": "tt-movie"}  # duplicate of the film
    return {}


async def test_search_any_merges_movies_first_and_dedupes(patch_tmdb):
    patch_tmdb(_any_handler)

    results = await tmdb_service.search_any("Дюна")

    ids = [r.imdb_id for r in results]
    assert ids == ["tt-movie", "tt-series"]  # movie first, duplicate dropped


# ── imdb-less hits, re-ranking, year qualifier ───────────────────────────────


def _imdbless_movie_handler(url, _params):
    if "/search/movie" in url:
        return {"results": [
            {"id": 99, "title": "Старый фильм", "release_date": "1957-05-01",
             "poster_path": "/x.jpg"},
        ]}
    if url.endswith("/movie/99"):
        return {"imdb_id": ""}  # no IMDb link
    return {}


async def test_search_keeps_imdbless_hit_as_synthetic_key(patch_tmdb):
    patch_tmdb(_imdbless_movie_handler)

    results = await tmdb_service.search("Старый фильм")

    assert len(results) == 1
    assert results[0].imdb_id == "tmdb:movie:99"
    assert results[0].year == "1957"
    assert results[0].poster_url.endswith("/x.jpg")


def _rerank_handler(url, _params):
    # The exact-title original sits BELOW a more "popular" sequel in TMDb order.
    if "/search/movie" in url:
        return {"results": [
            {"id": 1, "title": "Ирония судьбы, или С лёгким паром! 2",
             "release_date": "2007-12-20", "poster_path": "/a.jpg"},
            {"id": 2, "title": "Ирония судьбы, или С лёгким паром!",
             "release_date": "1975-01-01", "poster_path": "/b.jpg"},
        ]}
    if url.endswith("/movie/1"):
        return {"imdb_id": "tt-sequel"}
    if url.endswith("/movie/2"):
        return {"imdb_id": "tt-original"}
    return {}


async def test_search_reranks_exact_title_above_popular(patch_tmdb):
    patch_tmdb(_rerank_handler)

    results = await tmdb_service.search("Ирония судьбы, или С лёгким паром!")

    assert results[0].imdb_id == "tt-original"  # exact match floats to the top


def _year_handler_factory(captured):
    def _handler(url, params):
        if "/search/movie" in url:
            captured.update(params)
            return {"results": [
                {"id": 1, "title": "Ирония судьбы", "release_date": "2007-01-01",
                 "poster_path": "/a.jpg"},
                {"id": 2, "title": "Ирония судьбы", "release_date": "1975-01-01",
                 "poster_path": "/b.jpg"},
            ]}
        if url.endswith("/movie/1"):
            return {"imdb_id": "tt-2007"}
        if url.endswith("/movie/2"):
            return {"imdb_id": "tt-1975"}
        return {}
    return _handler


async def test_search_extracts_year_qualifier_and_boosts(patch_tmdb):
    captured: dict = {}
    patch_tmdb(_year_handler_factory(captured))

    results = await tmdb_service.search("Ирония судьбы (1975)")

    # Год вынесен из строки запроса (ищем по чистому названию)…
    assert captured.get("query") == "Ирония судьбы"
    # …но НЕ как жёсткий фильтр TMDb (его даты бывают на год смещены)…
    assert "primary_release_year" not in captured
    # …а как мягкий бонус: одноимённая запись нужного года всплывает выше.
    assert results[0].imdb_id == "tt-1975"


# ── get_by_key (TMDb-only metadata) ──────────────────────────────────────────


def _detail_handler(url, _params):
    if url.endswith("/movie/42"):
        return {
            "title": "Иди и смотри", "original_title": "Come and See",
            "release_date": "1985-07-09",
            "genres": [{"name": "Драма"}, {"name": "Военный"}],
            "overview": "Подросток в оккупированной Белоруссии.",
            "poster_path": "/p.jpg",
            "credits": {
                "cast": [{"name": "Алексей Кравченко"}, {"name": "Ольга Миронова"}],
                "crew": [{"job": "Writer", "name": "Алесь Адамович"},
                         {"job": "Director", "name": "Элем Климов"}],
            },
        }
    if url.endswith("/tv/7"):
        return {
            "name": "Семнадцать мгновений весны", "original_name": "Seventeen Moments",
            "first_air_date": "1973-08-11",
            "genres": [{"name": "Драма"}],
            "overview": "Советский разведчик в Берлине.",
            "poster_path": None,
            "created_by": [{"name": "Татьяна Лиознова"}],
            "credits": {"cast": [{"name": "Вячеслав Тихонов"}], "crew": []},
        }
    return {}


async def test_get_by_key_builds_moviebase_for_movie(patch_tmdb):
    patch_tmdb(_detail_handler)

    movie = await tmdb_service.get_by_key("tmdb:movie:42")

    assert movie is not None
    assert movie.imdb_id == "tmdb:movie:42"
    assert movie.title == "Иди и смотри"
    assert movie.original_title == "Come and See"
    assert movie.year == 1985
    assert movie.media_type == "movie"
    assert movie.genres == ["Драма", "Военный"]
    assert movie.director == "Элем Климов"  # picked from crew job=Director
    assert movie.cast[0] == "Алексей Кравченко"
    assert movie.poster_url.endswith("/p.jpg")
    assert movie.imdb_rating is None  # TMDb vote не подмешиваем под меткой IMDb


async def test_get_by_key_builds_moviebase_for_tv(patch_tmdb):
    patch_tmdb(_detail_handler)

    series = await tmdb_service.get_by_key("tmdb:tv:7")

    assert series is not None
    assert series.media_type == "series"
    assert series.year == 1973
    assert series.director == "Татьяна Лиознова"  # from created_by for TV
    assert series.poster_url is None


async def test_get_by_key_rejects_bad_key(patch_tmdb):
    patch_tmdb(_detail_handler)
    assert await tmdb_service.get_by_key("tt0137523") is None
    assert await tmdb_service.get_by_key("tmdb:bogus:1") is None


def test_is_tmdb_key_and_parse():
    from backend.services.tmdb import is_tmdb_key, parse_tmdb_key

    assert is_tmdb_key("tmdb:movie:1") is True
    assert is_tmdb_key("tt0137523") is False
    assert parse_tmdb_key("tmdb:tv:55") == ("tv", "55")
    assert parse_tmdb_key("tmdb:movie:x") is None
    assert parse_tmdb_key("tt0137523") is None
