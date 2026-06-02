"""Tests for the shared IMDb-rating formatting helpers."""

from __future__ import annotations

import pytest

from handlers.formatting import format_imdb_rating, imdb_suffix


# ── format_imdb_rating ────────────────────────────────────────────────────────


def test_format_strips_float32_noise():
    """8.6 stored as a 32-bit float round-trips to 8.600000381469727."""
    assert format_imdb_rating(8.600000381469727) == "8.6"
    assert format_imdb_rating(7.300000190734863) == "7.3"


def test_format_clean_value():
    assert format_imdb_rating(8.6) == "8.6"


def test_format_rounds_to_one_decimal():
    assert format_imdb_rating(7.349) == "7.3"  # rounds down
    assert format_imdb_rating(7.36) == "7.4"   # rounds up


def test_format_pads_whole_numbers():
    assert format_imdb_rating(9.0) == "9.0"
    assert format_imdb_rating(10) == "10.0"


def test_format_none_is_empty():
    assert format_imdb_rating(None) == ""


def test_format_zero_is_empty():
    """An unrated 0.0 reads as 'no rating' and is omitted."""
    assert format_imdb_rating(0.0) == ""


# ── imdb_suffix ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "prefix, expected",
    [
        (", IMDb ", ", IMDb 8.6"),
        (" | IMDb ", " | IMDb 8.6"),
        ("  ★ ", "  ★ 8.6"),
    ],
)
def test_suffix_applies_prefix(prefix, expected):
    assert imdb_suffix(8.600000381469727, prefix) == expected


def test_suffix_none_is_empty():
    assert imdb_suffix(None, ", IMDb ") == ""


def test_suffix_zero_is_empty():
    assert imdb_suffix(0.0, ", IMDb ") == ""
