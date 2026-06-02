"""Shared text-formatting helpers for Telegram handlers."""

from __future__ import annotations


def format_imdb_rating(rating: float | None) -> str:
    """Return the IMDb rating as ``"8.6"``, or ``""`` when there is none.

    IMDb ratings are stored as 32-bit floats (``imdb_rating REAL``), so the raw
    value carries floating-point noise — e.g. ``8.6`` round-trips to
    ``8.600000381469727``. Always round to one decimal place before showing it
    to the user.

    A missing rating (``None``) and an unrated ``0.0`` both yield ``""`` so the
    rating can simply be omitted from the message.
    """
    if not rating:
        return ""
    return f"{rating:.1f}"


def imdb_suffix(rating: float | None, prefix: str) -> str:
    """Return a ready-to-append rating suffix, or ``""`` when there's no rating.

    ``imdb_suffix(8.6, ", IMDb ")`` → ``", IMDb 8.6"``;
    ``imdb_suffix(None, ", IMDb ")`` → ``""``.

    ``prefix`` carries the per-message decoration (separator + label), which
    varies by call site, so it's explicit rather than defaulted.
    """
    formatted = format_imdb_rating(rating)
    return f"{prefix}{formatted}" if formatted else ""
