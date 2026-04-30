"""Smoke tests for health-check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_quick(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_full_reports_database(client):
    r = await client.get("/api/health/full")
    assert r.status_code == 200
    body = r.json()
    assert body["database"]["engine"] == "sqlite"
    assert body["database"]["ok"] is True
    # Binaries / secrets shape: present, well-formed
    assert "yt_dlp" in body["binaries"]
    assert "ffmpeg" in body["binaries"]
    assert "OMDB_API_KEY" in body["secrets"]
