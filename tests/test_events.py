"""Tests for the event analytics endpoint + insert helper.

Best-effort semantics matter: unknown event names are dropped, a DB failure
must NOT surface as a 500, and the bot writes events directly via insert_events.
"""

from __future__ import annotations

import aiosqlite
import pytest

from backend import database as db
from backend.config import DATABASE_PATH


async def _register(client, email: str) -> str:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "test-passw0rd-X", "name": "E"},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _fetchrow(query: str, params: tuple):
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        async with conn.execute(query, params) as cur:
            return await cur.fetchone()


async def test_events_filters_allowlist(client):
    r = await client.post(
        "/api/events",
        json={"events": [
            {"name": "app_open", "props": {"v": 1}, "anon_id": "anon-allow"},
            {"name": "totally_made_up_event"},  # dropped
        ]},
    )
    assert r.status_code == 200
    assert r.json()["accepted"] == 1
    # the junk name never landed
    assert await _fetchrow(
        "SELECT 1 FROM events WHERE name = ?", ("totally_made_up_event",)
    ) is None


async def test_events_guest_anon_id_stored(client):
    await client.post(
        "/api/events", json={"events": [{"name": "share_opened", "anon_id": "anon-guest"}]}
    )
    row = await _fetchrow(
        "SELECT user_id, anon_id, source FROM events "
        "WHERE name = 'share_opened' AND anon_id = ?",
        ("anon-guest",),
    )
    assert row is not None
    assert row[0] is None        # guest → no user_id
    assert row[1] == "anon-guest"
    assert row[2] == "web"


async def test_events_authed_stamps_user_id(client):
    token = await _register(client, "ev_auth@example.com")
    await client.post(
        "/api/events", headers=_auth(token),
        json={"events": [{"name": "movie_added", "anon_id": "anon-auth"}]},
    )
    row = await _fetchrow(
        "SELECT user_id FROM events WHERE name = 'movie_added' AND anon_id = ?",
        ("anon-auth",),
    )
    assert row is not None and row[0] is not None  # server stamped user_id


async def test_events_failure_does_not_500(client, monkeypatch):
    async def boom(rows):
        raise RuntimeError("db down")

    monkeypatch.setattr("backend.routers.events.db.insert_events", boom)
    r = await client.post("/api/events", json={"events": [{"name": "app_open"}]})
    assert r.status_code == 200  # analytics never breaks the client


async def test_events_batch_cap_rejected(client):
    too_many = {"events": [{"name": "app_open"} for _ in range(51)]}
    r = await client.post("/api/events", json=too_many)
    assert r.status_code == 422  # MAX_EVENTS_PER_BATCH guard


async def test_insert_events_bot_source(client):
    await db.insert_events([
        {"name": "app_open", "user_id": 4242, "source": "bot", "props": {"cmd": "start"}},
    ])
    row = await _fetchrow(
        "SELECT source, user_id FROM events WHERE source = 'bot' AND user_id = ?",
        (4242,),
    )
    assert row is not None and row[0] == "bot"
