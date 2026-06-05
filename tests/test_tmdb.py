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
            {  # no external imdb_id → must be dropped
                "id": 2,
                "name": "Безымянный сериал",
                "first_air_date": "2020-01-01",
                "poster_path": None,
            },
        ]}
    if url.endswith("/tv/1/external_ids"):
        return {"imdb_id": "tt32937780"}
    if url.endswith("/tv/2/external_ids"):
        return {"imdb_id": ""}  # empty → normalised to None → dropped
    return {}


async def test_search_tv_maps_series_fields(patch_tmdb):
    patch_tmdb(_tv_handler)

    results = await tmdb_service.search_tv("У меня очень плохое предчувствие")

    assert len(results) == 1  # the imdb-less one is dropped
    r = results[0]
    assert r.imdb_id == "tt32937780"
    assert r.title == "У меня очень плохое предчувствие"  # name preferred
    assert r.year == "2026"  # first_air_date[:4]
    assert r.poster_url and r.poster_url.endswith("/poster.jpg")


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
