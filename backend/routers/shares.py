"""Public read-only snapshots of a user's library, addressable by short slug.

Two creation modes:
- Authenticated: snapshot is taken from the user's current DB library at the
  moment of POST. The user's display name is captured for the share header.
- Guest: client sends ``library`` inline (whatever's in localStorage). The
  share gets an ``expires_at`` 90 days out so unclaimed guest snapshots don't
  pile up.

Reads (``GET /api/shares/{slug}``) are public and increment a view counter.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend import database as db
from backend.auth import get_current_user_optional
from backend.models import (
    Movie,
    SharedListCreateRequest,
    SharedListResponse,
    User,
)


router = APIRouter(prefix="/api/shares", tags=["shares"])


GUEST_TTL = timedelta(days=90)
SLUG_LENGTH = 8
MAX_SLUG_TRIES = 6
MAX_NAME_LENGTH = 80


async def _unique_slug() -> str:
    """Generate a short URL-safe slug that doesn't collide with existing rows.

    8 chars from token_urlsafe gives ~48 bits of entropy — collision odds are
    negligible at our scale. The retry loop is paranoia: if we're ever wrong,
    log a warning and bail rather than spinning forever.
    """
    for _ in range(MAX_SLUG_TRIES):
        slug = secrets.token_urlsafe(SLUG_LENGTH)[:SLUG_LENGTH]
        if not await db.slug_exists(slug):
            return slug
    raise HTTPException(
        status_code=500, detail="Could not generate a unique share id; try again",
    )


def _normalise_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Share name cannot be empty")
    return name[:MAX_NAME_LENGTH]


def _movies_to_snapshot(movies: list[Movie]) -> str:
    # ``user_note`` — личная заметка из дневника; в публичный шэр её не пускаем.
    # ``user_rating`` оставляем: курируемый список «мои 5★» — это и есть фича.
    return json.dumps(
        [m.model_dump(mode="json", exclude={"user_note"}) for m in movies]
    )


def _snapshot_to_movies(snapshot: str) -> list[Movie]:
    try:
        raw = json.loads(snapshot)
    except (TypeError, ValueError):
        return []
    return [Movie.model_validate(m) for m in raw if isinstance(m, dict)]


@router.post("", response_model=SharedListResponse)
async def create_shared_list(
    payload: SharedListCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> SharedListResponse:
    name = _normalise_name(payload.name)

    if current_user is not None:
        # Authenticated path: snapshot the user's library straight from DB so
        # what gets shared can't lie about what they have.
        movies = await db.get_all_movies(
            user_id=current_user.id, in_library=True,
        )
        owner_user_id = current_user.id
        owner_name = current_user.name or current_user.email.split("@")[0]
        expires_at: Optional[datetime] = None
    else:
        if not payload.library:
            raise HTTPException(
                status_code=422,
                detail="Guest shares require a non-empty library in the request",
            )
        movies = payload.library
        owner_user_id = None
        owner_name = None
        expires_at = datetime.utcnow() + GUEST_TTL

    if not movies:
        raise HTTPException(
            status_code=422, detail="Cannot share an empty library",
        )

    slug = await _unique_slug()
    snapshot_json = _movies_to_snapshot(movies)
    row = await db.create_share(
        slug=slug,
        owner_user_id=owner_user_id,
        name=name,
        snapshot_json=snapshot_json,
        expires_at=expires_at,
    )

    return SharedListResponse(
        slug=row["slug"],
        name=row["name"],
        owner_name=owner_name,
        created_at=row["created_at"],
        movies=movies,
    )


@router.get("/{slug}", response_model=SharedListResponse)
async def get_shared_list(slug: str) -> SharedListResponse:
    row = await db.get_share_by_slug(slug)
    if not row:
        raise HTTPException(status_code=404, detail="Share not found or expired")

    owner_name: Optional[str] = None
    if row["owner_user_id"]:
        owner_row = await db.get_user_by_id(row["owner_user_id"])
        if owner_row:
            owner_name = owner_row.get("name") or (
                owner_row.get("email", "").split("@")[0] or None
            )

    return SharedListResponse(
        slug=row["slug"],
        name=row["name"],
        owner_name=owner_name,
        created_at=row["created_at"],
        movies=_snapshot_to_movies(row["snapshot"]),
    )
