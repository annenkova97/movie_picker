"""Rate-limiting behaviour (slowapi).

The suite runs with RATE_LIMIT_ENABLED=0 (see conftest) so ordinary tests don't
trip the per-IP limits. These tests flip the limiter on for themselves and put
it back afterwards, then assert that crossing a limit yields HTTP 429.
"""

from __future__ import annotations

import pytest

from backend.rate_limit import limiter


@pytest.fixture
def rate_limiting_on():
    """Enable the shared limiter with a clean store, restore it afterwards."""
    previous = limiter.enabled
    _reset_limiter()
    limiter.enabled = True
    try:
        yield
    finally:
        limiter.enabled = previous
        _reset_limiter()


def _reset_limiter() -> None:
    """Clear accumulated counters so tests don't bleed into each other."""
    reset = getattr(limiter, "reset", None)
    if callable(reset):
        try:
            reset()
        except Exception:
            pass


# /auth/login is the tightest auth limit that has no side effects (bad creds
# return 401 without touching the DB), so it's the cleanest endpoint to probe.
LOGIN_LIMIT = 10
LOGIN_BODY = {"email": "nobody@example.com", "password": "wrong-password-123"}


@pytest.mark.asyncio
async def test_login_is_rate_limited(client, rate_limiting_on):
    # First LOGIN_LIMIT requests are allowed through (and fail auth with 401).
    for i in range(LOGIN_LIMIT):
        resp = await client.post("/auth/login", json=LOGIN_BODY)
        assert resp.status_code == 401, f"call {i + 1} should pass the limiter, got {resp.status_code}"

    # The next one crosses the limit.
    blocked = await client.post("/auth/login", json=LOGIN_BODY)
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_disabled_limiter_never_blocks(client):
    """With the suite default (RATE_LIMIT_ENABLED=0) the limiter is inert."""
    assert limiter.enabled is False
    for _ in range(LOGIN_LIMIT + 5):
        resp = await client.post("/auth/login", json=LOGIN_BODY)
        assert resp.status_code == 401  # always auth failure, never 429
