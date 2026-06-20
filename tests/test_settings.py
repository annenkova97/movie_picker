"""Tests for the user availability settings endpoint (region + services)."""

from __future__ import annotations

import pytest


async def _register(client, email: str) -> str:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "test-passw0rd-X", "name": "S"},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_settings_requires_auth(client):
    assert (await client.get("/api/settings")).status_code == 401
    assert (await client.patch("/api/settings", json={"region": "US"})).status_code == 401


async def test_settings_defaults(client):
    token = await _register(client, "settings_def@example.com")
    r = await client.get("/api/settings", headers=_auth(token))
    assert r.status_code == 200
    assert r.json() == {"region": "RU", "streaming_services": []}


async def test_settings_patch_partial_and_persists(client):
    token = await _register(client, "settings_patch@example.com")

    # set services only — region keeps its default
    r = await client.patch(
        "/api/settings", headers=_auth(token), json={"streaming_services": [8, 119]}
    )
    assert r.status_code == 200
    assert r.json() == {"region": "RU", "streaming_services": [8, 119]}

    # set region only (lowercase) — services persist, region is uppercased
    r2 = await client.patch(
        "/api/settings", headers=_auth(token), json={"region": "us"}
    )
    assert r2.json() == {"region": "US", "streaming_services": [8, 119]}

    # GET reflects the stored state
    r3 = await client.get("/api/settings", headers=_auth(token))
    assert r3.json() == {"region": "US", "streaming_services": [8, 119]}


async def test_settings_rejects_bad_region(client):
    token = await _register(client, "settings_bad@example.com")
    r = await client.patch(
        "/api/settings", headers=_auth(token), json={"region": "USA"}
    )
    assert r.status_code == 422  # region is a 2-letter country code


async def test_settings_are_per_user(client):
    t1 = await _register(client, "settings_u1@example.com")
    t2 = await _register(client, "settings_u2@example.com")
    await client.patch("/api/settings", headers=_auth(t1), json={"streaming_services": [8]})
    # u2 untouched
    assert (await client.get("/api/settings", headers=_auth(t2))).json()[
        "streaming_services"
    ] == []
