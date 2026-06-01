"""Test configuration: force a clean throwaway SQLite DB for every session.

Env vars must be set BEFORE backend.* gets imported, because backend.config
captures DATABASE_PATH at import time. Doing it at the top of this file (which
pytest loads before collecting tests) is the simplest correct ordering.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio


# Throwaway SQLite db for the whole test session.
_TMP = tempfile.NamedTemporaryFile(prefix="lentochka_test_", suffix=".db", delete=False)
_TMP.close()
os.environ["DATABASE_PATH"] = _TMP.name
os.environ.pop("DATABASE_URL", None)  # always test against SQLite

# Skip awards-seed during tests — it's slow and not relevant to anything we test.
os.environ.setdefault("SKIP_AWARDS_SEED", "1")

# backend.config refuses to start without JWT_SECRET — give the suite a fixed one.
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789abcdef")

# Rate limiting off by default so ordinary tests don't trip the per-IP limits
# (register is only 5/hour). The dedicated test in test_rate_limit.py flips the
# limiter back on for itself.
os.environ.setdefault("RATE_LIMIT_ENABLED", "0")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _bootstrap_db():
    """Run init_db once before any test, and clean up the file at the end."""
    from backend import database as db
    await db.init_db()
    yield
    try:
        Path(_TMP.name).unlink(missing_ok=True)
    except OSError:
        pass


@pytest_asyncio.fixture
async def client() -> AsyncIterator:
    """ASGI HTTP client bound to the FastAPI app."""
    from httpx import AsyncClient, ASGITransport
    from backend.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
