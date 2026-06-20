"""Tests for watch-provider availability: TMDb fetch, cache TTL, filter, endpoint.

No network — ``httpx`` is faked for the TMDb-parsing tests, and the cache-layer
tests stub ``tmdb_service.get_watch_providers`` directly so we exercise the
cache-or-fetch logic against the real (throwaway) SQLite DB.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from unittest.mock import AsyncMock

import backend.services.tmdb as tmdb_mod
from backend.services.tmdb import tmdb_service
from backend.services import availability as avail_mod
from backend.services.availability import get_availability, is_available_on
from backend import database as db


# ── tiny httpx fake (URL-routing handler) ────────────────────────────────────


class _Resp:
    def __init__(self, data: dict) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._data


class _FakeClient:
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
    monkeypatch.setattr(tmdb_service, "api_key", "test-key")

    def _install(handler):
        monkeypatch.setattr(
            tmdb_mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient(handler)
        )

    return _install


# Normalized provider payload reused across cache tests.
_NETFLIX = {
    "region": "RU", "link": "https://justwatch/x",
    "flatrate": [{"provider_id": 8, "name": "Netflix", "logo_url": None}],
    "rent": [], "buy": [],
}


# ── resolve_tmdb_ref ─────────────────────────────────────────────────────────


async def test_resolve_ref_synthetic_key_no_network(patch_tmdb):
    # Bogus handler asserts we never hit it for a synthetic key.
    patch_tmdb(lambda url, params: (_ for _ in ()).throw(AssertionError("no http")))
    assert await tmdb_service.resolve_tmdb_ref("tmdb:movie:42") == ("movie", "42")
    assert await tmdb_service.resolve_tmdb_ref("tmdb:tv:7") == ("tv", "7")


async def test_resolve_ref_tt_via_find(patch_tmdb):
    def handler(url, _p):
        if "/find/tt0111161" in url:
            return {"movie_results": [{"id": 278}], "tv_results": []}
        return {}
    patch_tmdb(handler)
    assert await tmdb_service.resolve_tmdb_ref("tt0111161") == ("movie", "278")


async def test_resolve_ref_tt_tv_result(patch_tmdb):
    def handler(url, _p):
        if "/find/tt999" in url:
            return {"movie_results": [], "tv_results": [{"id": 55}]}
        return {}
    patch_tmdb(handler)
    assert await tmdb_service.resolve_tmdb_ref("tt999") == ("tv", "55")


async def test_resolve_ref_no_hit_returns_none(patch_tmdb):
    patch_tmdb(lambda url, _p: {"movie_results": [], "tv_results": []})
    assert await tmdb_service.resolve_tmdb_ref("tt000") is None


async def test_resolve_ref_disabled_returns_none(monkeypatch, patch_tmdb):
    patch_tmdb(lambda url, _p: {})
    monkeypatch.setattr(tmdb_service, "api_key", "")
    assert await tmdb_service.resolve_tmdb_ref("tt0111161") is None


# ── get_watch_providers ──────────────────────────────────────────────────────


async def test_get_watch_providers_normalizes_and_sorts(patch_tmdb):
    def handler(url, _p):
        if url.endswith("/movie/42/watch/providers"):
            return {"results": {"RU": {
                "link": "https://justwatch/come-and-see",
                "flatrate": [
                    {"provider_id": 119, "provider_name": "Amazon", "logo_path": "/a.jpg", "display_priority": 5},
                    {"provider_id": 8, "provider_name": "Netflix", "logo_path": "/n.jpg", "display_priority": 1},
                ],
                "rent": [{"provider_id": 2, "provider_name": "Apple TV", "logo_path": None, "display_priority": 1}],
            }}}
        return {}
    patch_tmdb(handler)

    av = await tmdb_service.get_watch_providers("tmdb:movie:42", "ru")

    assert av["region"] == "RU"  # uppercased
    assert av["link"].endswith("/come-and-see")
    # display_priority orders Netflix (1) before Amazon (5)
    assert [p["name"] for p in av["flatrate"]] == ["Netflix", "Amazon"]
    assert av["flatrate"][0]["logo_url"].endswith("/n.jpg")  # full logo URL
    assert av["rent"][0]["name"] == "Apple TV"
    assert av["buy"] == []


async def test_get_watch_providers_missing_region_is_empty(patch_tmdb):
    patch_tmdb(lambda url, _p: {"results": {"US": {"flatrate": []}}})
    av = await tmdb_service.get_watch_providers("tmdb:movie:42", "RU")
    assert av == {"region": "RU", "link": None, "flatrate": [], "rent": [], "buy": []}


async def test_get_watch_providers_disabled_returns_none(monkeypatch, patch_tmdb):
    patch_tmdb(lambda url, _p: {})
    monkeypatch.setattr(tmdb_service, "api_key", "")
    assert await tmdb_service.get_watch_providers("tmdb:movie:42", "RU") is None


# ── cache-or-fetch service ───────────────────────────────────────────────────


async def test_get_availability_caches_within_ttl(monkeypatch):
    calls = {"n": 0}

    async def fake(key, region):
        calls["n"] += 1
        return dict(_NETFLIX)

    monkeypatch.setattr(avail_mod.tmdb_service, "get_watch_providers", fake)

    first = await get_availability("tt_cache_a", "RU")
    second = await get_availability("tt_cache_a", "RU")

    assert first["flatrate"][0]["provider_id"] == 8
    assert second == first
    assert calls["n"] == 1  # second served from cache, no refetch


async def test_get_availability_refetches_when_stale(monkeypatch):
    calls = {"n": 0}

    async def fake(key, region):
        calls["n"] += 1
        return dict(_NETFLIX)

    monkeypatch.setattr(avail_mod.tmdb_service, "get_watch_providers", fake)
    monkeypatch.setattr(avail_mod, "CACHE_TTL", timedelta(0))  # everything stale

    await get_availability("tt_cache_b", "RU")
    await get_availability("tt_cache_b", "RU")
    assert calls["n"] == 2  # stale → refetch each time


async def test_get_availability_returns_stale_on_fetch_failure(monkeypatch):
    await db.upsert_watch_providers_cache("tt_cache_c", "RU", dict(_NETFLIX))
    monkeypatch.setattr(avail_mod, "CACHE_TTL", timedelta(0))  # force stale
    monkeypatch.setattr(
        avail_mod.tmdb_service, "get_watch_providers", AsyncMock(return_value=None)
    )
    result = await get_availability("tt_cache_c", "RU")
    assert result["flatrate"][0]["provider_id"] == 8  # stale cache served


async def test_get_availability_none_when_no_data(monkeypatch):
    monkeypatch.setattr(
        avail_mod.tmdb_service, "get_watch_providers", AsyncMock(return_value=None)
    )
    assert await get_availability("tt_never_seen", "RU") is None


# ── is_available_on ──────────────────────────────────────────────────────────


def test_is_available_on_matches_flatrate():
    assert is_available_on(_NETFLIX, [8]) is True
    assert is_available_on(_NETFLIX, [337]) is False
    assert is_available_on(_NETFLIX, []) is False
    assert is_available_on(None, [8]) is False


def test_is_available_on_ignores_rent_buy():
    only_rent = {"region": "RU", "link": None, "flatrate": [],
                 "rent": [{"provider_id": 2, "name": "Apple TV", "logo_url": None}], "buy": []}
    assert is_available_on(only_rent, [2]) is False


# ── /api/availability endpoint ───────────────────────────────────────────────


async def test_availability_endpoint_returns_shape(client, monkeypatch):
    monkeypatch.setattr(
        avail_mod.tmdb_service, "get_watch_providers",
        AsyncMock(return_value=dict(_NETFLIX)),
    )
    r = await client.get("/api/availability/tt_ep_1?region=RU")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "RU"
    assert body["flatrate"][0]["name"] == "Netflix"


async def test_availability_endpoint_empty_when_no_data(client, monkeypatch):
    monkeypatch.setattr(
        avail_mod.tmdb_service, "get_watch_providers", AsyncMock(return_value=None)
    )
    r = await client.get("/api/availability/tt_ep_missing?region=US")
    assert r.status_code == 200
    assert r.json() == {
        "region": "US", "link": None, "flatrate": [], "rent": [], "buy": [],
    }
