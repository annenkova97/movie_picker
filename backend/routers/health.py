"""Diagnostic endpoint for production sanity-checks.

Reports the state of every external dependency the app needs:
- ffmpeg/ffprobe (audio extraction for Whisper)
- Apify token (Instagram parsing)
- DB engine (SQLite vs PostgreSQL) and a live SELECT 1
- Required API keys set or missing

Public — no auth — but only exposes booleans / versions, nothing sensitive.
Hit it with: curl https://<host>/api/health/full
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from backend import config


router = APIRouter(prefix="/api/health", tags=["health"])


def _bin_version(name: str, args: list[str] | None = None) -> dict[str, Any]:
    """Return {ok, path, version, error} for a binary on PATH."""
    args = args or ["--version"]
    path = shutil.which(name)
    if not path:
        for cand in [f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}"]:
            try:
                # Cheap existence check without touching FS metadata cost
                with open(cand, "rb"):
                    path = cand
                    break
            except OSError:
                continue
    if not path:
        return {"ok": False, "path": None, "version": None, "error": "not found in PATH"}

    try:
        out = subprocess.run(
            [path, *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else ""
        return {"ok": out.returncode == 0, "path": path, "version": version, "error": None}
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "path": path, "version": None, "error": str(exc)}


async def _db_probe() -> dict[str, Any]:
    """Run a trivial query against whichever engine is active."""
    engine = "postgresql" if config.USE_POSTGRES else "sqlite"
    try:
        if config.USE_POSTGRES:
            from backend import db_postgres
            pool = db_postgres._pool
            if pool is None:
                return {"engine": engine, "ok": False, "error": "pool not initialised"}
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        else:
            import aiosqlite
            async with aiosqlite.connect(config.DATABASE_PATH) as conn:
                await conn.execute("SELECT 1")
        return {"engine": engine, "ok": True, "error": None}
    except Exception as exc:
        return {"engine": engine, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _key_state(value: str) -> dict[str, Any]:
    """Booleanish status of an env-var-backed secret, without leaking it."""
    return {"set": bool(value), "length": len(value) if value else 0}


@router.get("")
async def health_quick() -> dict[str, Any]:
    """Liveness check — fast, used by Railway/uptime monitors."""
    return {"status": "ok"}


@router.get("/full")
async def health_full() -> dict[str, Any]:
    """Full diagnostic — checks every external dep. Public, but read-only."""
    ffmpeg_info = await run_in_threadpool(_bin_version, "ffmpeg", ["-version"])
    ffprobe_info = await run_in_threadpool(_bin_version, "ffprobe", ["-version"])
    db_info = await _db_probe()

    overall_ok = (
        ffmpeg_info["ok"]
        and ffprobe_info["ok"]
        and db_info["ok"]
        and bool(config.APIFY_TOKEN)
    )

    return {
        "ok": overall_ok,
        "binaries": {
            "ffmpeg": ffmpeg_info,
            "ffprobe": ffprobe_info,
        },
        "database": db_info,
        "secrets": {
            "OMDB_API_KEY": _key_state(config.OMDB_API_KEY),
            "ANTHROPIC_API_KEY": _key_state(config.ANTHROPIC_API_KEY),
            "OPENAI_API_KEY": _key_state(config.OPENAI_API_KEY),
            "TELEGRAM_BOT_TOKEN": _key_state(config.TELEGRAM_BOT_TOKEN),
            "APIFY_TOKEN": _key_state(config.APIFY_TOKEN),
            "JWT_SECRET": {"set": config.JWT_SECRET != "dev-only-insecure-secret-change-me"},
            "GOOGLE_CLIENT_ID": _key_state(config.GOOGLE_CLIENT_ID),
        },
        "instagram": {
            "backend": "apify",
            "actor": config.APIFY_INSTAGRAM_ACTOR,
            "token_set": bool(config.APIFY_TOKEN),
        },
    }
