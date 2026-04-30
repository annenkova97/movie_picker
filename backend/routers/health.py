"""Diagnostic endpoint for production sanity-checks.

Reports the state of every external dependency the app needs:
- yt-dlp + ffmpeg/ffprobe (Instagram pipeline)
- DB engine (SQLite vs PostgreSQL) and a live SELECT 1
- Required API keys set or missing
- INSTAGRAM_COOKIES_PATH presence

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
from backend import database as db


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
    yt_dlp_info = await run_in_threadpool(_bin_version, "yt-dlp")
    ffmpeg_info = await run_in_threadpool(_bin_version, "ffmpeg", ["-version"])
    ffprobe_info = await run_in_threadpool(_bin_version, "ffprobe", ["-version"])
    db_info = await _db_probe()

    cookies_path = config.INSTAGRAM_COOKIES_PATH
    cookies_present = False
    try:
        with open(cookies_path, "rb"):
            cookies_present = True
    except OSError:
        cookies_present = False

    overall_ok = (
        yt_dlp_info["ok"]
        and ffmpeg_info["ok"]
        and ffprobe_info["ok"]
        and db_info["ok"]
    )

    return {
        "ok": overall_ok,
        "binaries": {
            "yt_dlp": yt_dlp_info,
            "ffmpeg": ffmpeg_info,
            "ffprobe": ffprobe_info,
        },
        "database": db_info,
        "secrets": {
            "OMDB_API_KEY": _key_state(config.OMDB_API_KEY),
            "ANTHROPIC_API_KEY": _key_state(config.ANTHROPIC_API_KEY),
            "OPENAI_API_KEY": _key_state(config.OPENAI_API_KEY),
            "TELEGRAM_BOT_TOKEN": _key_state(config.TELEGRAM_BOT_TOKEN),
            "JWT_SECRET": {"set": config.JWT_SECRET != "dev-only-insecure-secret-change-me"},
            "GOOGLE_CLIENT_ID": _key_state(config.GOOGLE_CLIENT_ID),
        },
        "instagram": {
            "cookies_path": cookies_path,
            "cookies_present": cookies_present,
        },
    }


@router.get("/yt-dlp-probe")
async def yt_dlp_probe(url: str) -> dict[str, Any]:
    """Try to fetch metadata for a URL with yt-dlp without downloading.

    Use this to verify yt-dlp can reach Instagram (or any provider) from prod
    without paying the cost of a full download. Pass any public Reel URL.
    """
    yt_dlp_path = shutil.which("yt-dlp") or "/opt/homebrew/bin/yt-dlp"

    cmd = [yt_dlp_path, "--dump-json", "--skip-download", "--no-warnings", url]
    if config.INSTAGRAM_COOKIES_PATH:
        try:
            with open(config.INSTAGRAM_COOKIES_PATH, "rb"):
                cmd[1:1] = ["--cookies", config.INSTAGRAM_COOKIES_PATH]
        except OSError:
            pass

    def _run() -> dict[str, Any]:
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "ok": out.returncode == 0,
                "exit_code": out.returncode,
                "stderr_tail": (out.stderr or "").strip().splitlines()[-5:],
                "title_seen": "title" in (out.stdout or "")[:5000],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "exit_code": None, "stderr_tail": ["timeout after 30s"], "title_seen": False}

    return await run_in_threadpool(_run)
