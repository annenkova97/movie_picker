from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.models.movie import Movie


class SharedListCreateRequest(BaseModel):
    """Request body for POST /api/shares.

    ``library`` is required for guest creators (no auth) and ignored when the
    request comes from an authenticated user — for them, we snapshot whatever
    is currently in the DB so the share can't drift from the source of truth.
    """
    name: str
    library: Optional[list[Movie]] = None


class SharedListResponse(BaseModel):
    """What GET /api/shares/{slug} returns. Read-only public view."""
    slug: str
    name: str
    owner_name: Optional[str]
    created_at: datetime
    movies: list[Movie]
