"""Unit tests for the Apify scraper layer. No network.

Covers two things:

* ``_is_error_item`` — recognising the *error record* that
  ``instagram-reel-scraper`` returns for unavailable Reels
  (``{"error": "no_items", ...}``) instead of treating it as an empty post.

* ``parse_reel_movies`` — the caption-first ladder that spends Apify credits
  step by step (caption → transcript without video → comments → vision) and
  stops at the first movie found, plus the per-shortcode cache that makes a
  repeat parse of the same Reel cost nothing.
"""

from __future__ import annotations

import pytest

import backend.services.instagram_reader as ir
from backend.services.instagram_reader import (
    InstagramReaderError,
    MovieInfo,
    _is_error_item,
    clear_parse_cache,
    parse_reel_movies,
)

URL = "https://www.instagram.com/reel/DZIqe2ZottC/"

# Sentinel: when this token is in any text the fake extractor "finds" a movie.
FILM = "ФИЛЬМ"


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


# ── parse_reel_movies ladder ─────────────────────────────────────────────────


@pytest.fixture
def stub(monkeypatch):
    """Stub every Apify/LLM boundary and count how deep the ladder went."""
    clear_parse_cache()
    monkeypatch.setattr(ir, "_ensure_apify_token", lambda: None)

    calls = {
        "caption": 0, "text": 0, "comments": 0, "video": 0,
        "frames": 0, "cleanup": 0, "extract": 0,
    }
    # Each stage's canned return value; tests override before calling.
    rv = {
        "caption": "", "text": ("", ""), "comments": "", "video": None,
    }

    def _caption(url):
        calls["caption"] += 1
        return rv["caption"]

    def _text(url):
        calls["text"] += 1
        return rv["text"]

    def _comments(url, **kw):
        calls["comments"] += 1
        return rv["comments"]

    def _video(url):
        calls["video"] += 1
        return rv["video"]

    def _frames(path, count=3):
        calls["frames"] += 1
        return [f"frame_{i}.jpg" for i in range(count)]

    def _cleanup(paths):
        calls["cleanup"] += 1

    def _extract(transcript="", caption="", frame_paths=None,
                 use_vision=False, comments=""):
        calls["extract"] += 1
        blob = f"{transcript} {caption} {comments}"
        if FILM in blob:
            return [MovieInfo("Начало", "Inception", "", "")]
        if use_vision and frame_paths:
            return [MovieInfo("Постер", "Poster", "", "")]
        return []

    monkeypatch.setattr(ir, "_caption_via_general_scraper", _caption)
    monkeypatch.setattr(ir, "_fetch_reel_text", _text)
    monkeypatch.setattr(ir, "fetch_top_comments", _comments)
    monkeypatch.setattr(ir, "_fetch_reel_video", _video)
    monkeypatch.setattr(ir, "extract_frames", _frames)
    monkeypatch.setattr(ir, "cleanup_temp_files", _cleanup)
    monkeypatch.setattr(ir, "extract_movies", _extract)

    return calls, rv


def test_caption_hit_skips_transcript_comments_video(stub):
    calls, rv = stub
    rv["caption"] = f"Делюсь, это {FILM} Начало"

    movies, caption, transcript = parse_reel_movies(URL)

    assert [m.title_en for m in movies] == ["Inception"]
    assert transcript == ""
    # The whole point: a title in the caption costs one cheap scrape, nothing else.
    assert calls["caption"] == 1
    assert calls["text"] == 0
    assert calls["comments"] == 0
    assert calls["video"] == 0
    assert calls["extract"] == 1


def test_escalates_to_transcript_when_caption_has_no_title(stub):
    calls, rv = stub
    rv["caption"] = ""                       # general scraper got nothing
    rv["text"] = ("", f"в озвучке назвали {FILM}")

    movies, _caption, transcript = parse_reel_movies(URL)

    assert [m.title_en for m in movies] == ["Inception"]
    assert transcript == f"в озвучке назвали {FILM}"
    assert calls["text"] == 1
    assert calls["comments"] == 0           # found in transcript → no comments
    assert calls["video"] == 0


def test_escalates_to_comments_when_text_has_no_title(stub):
    calls, rv = stub
    rv["caption"] = "просто подпись без названия"   # opened, but no film
    rv["text"] = ("", "болтовня без названия")
    rv["comments"] = f"- это же {FILM} Начало (200 likes)"

    movies, _caption, _transcript = parse_reel_movies(URL)

    assert [m.title_en for m in movies] == ["Inception"]
    assert calls["comments"] == 1
    assert calls["video"] == 0              # comments succeeded → no video


def test_raises_when_reel_did_not_open(stub):
    calls, rv = stub
    rv["caption"] = ""
    rv["text"] = ("", "")

    with pytest.raises(InstagramReaderError) as exc:
        parse_reel_movies(URL)
    assert "Не удалось открыть" in str(exc.value)
    assert calls["comments"] == 0           # never reached the comments stage


def test_no_duplicate_extract_when_only_general_caption(stub):
    # General caption present but filmless, reel-scraper adds no new text →
    # we must NOT re-run the identical extraction, and must not raise.
    calls, rv = stub
    rv["caption"] = "подпись без фильма"
    rv["text"] = ("", "")                    # no transcript, no extra caption
    rv["comments"] = ""

    movies, _caption, _transcript = parse_reel_movies(URL)

    assert movies == []
    assert calls["extract"] == 1            # caption extracted once, not twice


def test_vision_tier_used_only_when_requested(stub):
    calls, rv = stub
    rv["caption"] = "кадр без подписи-названия"  # opened, no film in text
    rv["text"] = ("", "")
    rv["comments"] = ""
    rv["video"] = "/tmp/reel.mp4"

    movies, _caption, _transcript = parse_reel_movies(URL, vision=True)

    assert [m.title_en for m in movies] == ["Poster"]
    assert calls["video"] == 1
    assert calls["frames"] == 1
    assert calls["cleanup"] == 1           # frames cleaned up after extract


def test_vision_not_touched_by_default(stub):
    calls, rv = stub
    rv["caption"] = "кадр без подписи-названия"
    rv["text"] = ("", "")
    rv["comments"] = ""

    movies, _caption, _transcript = parse_reel_movies(URL)  # vision defaults off

    assert movies == []
    assert calls["video"] == 0


# ── cache ────────────────────────────────────────────────────────────────────


def test_cache_hit_skips_all_apify(stub):
    calls, rv = stub
    rv["caption"] = f"это {FILM} Начало"

    first = parse_reel_movies(URL)
    second = parse_reel_movies(URL)

    assert second == first
    # Second call served from cache: no extra scrape, no extra LLM call.
    assert calls["caption"] == 1
    assert calls["extract"] == 1


def test_cache_also_remembers_empty_result(stub):
    # A filmless-but-opened Reel is deterministic → cache it so a re-send is free.
    calls, rv = stub
    rv["caption"] = "подпись без фильма"
    rv["text"] = ("", "")

    assert parse_reel_movies(URL)[0] == []
    assert parse_reel_movies(URL)[0] == []
    assert calls["caption"] == 1           # second call hit the cache
    assert calls["text"] == 1


def test_failed_open_is_not_cached(stub):
    # A raise may be a transient Apify hiccup — must stay retryable, not cached.
    calls, rv = stub
    rv["caption"] = ""
    rv["text"] = ("", "")

    with pytest.raises(InstagramReaderError):
        parse_reel_movies(URL)
    with pytest.raises(InstagramReaderError):
        parse_reel_movies(URL)
    assert calls["caption"] == 2           # retried, not served from cache
