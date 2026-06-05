"""Unit tests for the Apify scraper layer — error detection + fallback. No network.

Covers the bug where ``instagram-reel-scraper`` returns an *error record* for
some Reels (``{"error": "no_items", ...}``), which used to be silently treated
as an empty post. Now: such a record makes ``_call_apify_reel`` raise, and
``download_reel`` falls back to the general scraper; if both yield nothing it
raises a truthful error instead of pretending there were no films.
"""

from __future__ import annotations

import pytest

import backend.services.instagram_reader as ir
from backend.services.instagram_reader import (
    InstagramReaderError,
    _is_error_item,
    download_reel,
)

URL = "https://www.instagram.com/reel/DZIqe2ZottC/"


# ── _is_error_item ───────────────────────────────────────────────────────────


def test_is_error_item_true_for_error_record():
    assert _is_error_item(
        {"error": "no_items", "errorDescription": "Empty or private data"}
    ) is True


def test_is_error_item_false_when_caption_present():
    # An error flag plus real content → still usable, not an error record.
    assert _is_error_item({"error": "x", "caption": "Про сериал"}) is False


def test_is_error_item_false_for_normal_and_empty():
    assert _is_error_item({"caption": "hi"}) is False
    assert _is_error_item({}) is False


# ── _call_apify_reel error-record detection ──────────────────────────────────


def test_call_apify_reel_raises_on_error_record(monkeypatch):
    monkeypatch.setattr(ir, "_ensure_apify_token", lambda: None)
    monkeypatch.setattr(
        ir, "_run_apify_actor",
        lambda *a, **k: {"error": "no_items",
                         "errorDescription": "Empty or private data"},
    )
    with pytest.raises(InstagramReaderError) as exc:
        ir._call_apify_reel(URL)
    assert "Empty or private data" in str(exc.value)


def test_call_apify_reel_returns_good_item(monkeypatch):
    monkeypatch.setattr(ir, "_ensure_apify_token", lambda: None)
    item = {"caption": "Про фильм", "transcript": "t"}
    monkeypatch.setattr(ir, "_run_apify_actor", lambda *a, **k: item)
    assert ir._call_apify_reel(URL) is item


# ── download_reel orchestration ──────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _no_token_check(monkeypatch):
    monkeypatch.setattr(ir, "_ensure_apify_token", lambda: None)


def test_download_reel_uses_primary_and_skips_fallback(monkeypatch):
    calls = {"general": 0}

    monkeypatch.setattr(
        ir, "_call_apify_reel",
        lambda url: {"caption": "Про фильм Начало", "transcript": "t"},
    )

    def _general(url):
        calls["general"] += 1
        return "should-not-be-used"

    monkeypatch.setattr(ir, "_caption_via_general_scraper", _general)

    video, caption, transcript = download_reel(URL)

    assert video is None  # no downloadedVideo in the item
    assert caption == "Про фильм Начало"
    assert transcript == "t"
    assert calls["general"] == 0  # primary had text → fallback untouched


def test_download_reel_falls_back_to_general_scraper(monkeypatch):
    def _reel_fails(url):
        raise InstagramReaderError("reel-scraper не отдал данные: Empty or private data")

    monkeypatch.setattr(ir, "_call_apify_reel", _reel_fails)
    monkeypatch.setattr(
        ir, "_caption_via_general_scraper",
        lambda url: "делюсь сериалом «У меня очень плохое предчувствие»",
    )

    video, caption, transcript = download_reel(URL)

    assert video is None
    assert "У меня очень плохое предчувствие" in caption
    assert transcript == ""  # general scraper has no transcript


def test_download_reel_raises_truthfully_when_both_empty(monkeypatch):
    monkeypatch.setattr(
        ir, "_call_apify_reel",
        lambda url: (_ for _ in ()).throw(InstagramReaderError("nope")),
    )
    monkeypatch.setattr(ir, "_caption_via_general_scraper", lambda url: "")

    with pytest.raises(InstagramReaderError) as exc:
        download_reel(URL)
    assert "Не удалось открыть" in str(exc.value)


def test_download_reel_falls_back_when_primary_text_empty(monkeypatch):
    # Primary returns an item but with blank caption/transcript → still fall back.
    monkeypatch.setattr(
        ir, "_call_apify_reel",
        lambda url: {"caption": "   ", "transcript": ""},
    )
    monkeypatch.setattr(
        ir, "_caption_via_general_scraper", lambda url: "Реальный сериал",
    )

    _video, caption, _transcript = download_reel(URL)
    assert caption == "Реальный сериал"
