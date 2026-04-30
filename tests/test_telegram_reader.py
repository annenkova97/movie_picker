"""Unit tests for the Telegram t.me web parser. No network."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from backend.services.telegram_reader import (
    TelegramReaderError,
    fetch_post,
    validate_url,
)


# ── URL validation ──────────────────────────────────────────────────────────


def test_validate_url_canonicalises_valid_link():
    canon, channel, post_id = validate_url("https://t.me/durov/172")
    assert canon == "https://t.me/durov/172"
    assert channel == "durov"
    assert post_id == "172"


def test_validate_url_strips_trailing_slash():
    canon, _, _ = validate_url("https://t.me/some_chan/55/")
    assert canon == "https://t.me/some_chan/55"


def test_validate_url_accepts_www_prefix():
    canon, channel, post_id = validate_url("https://www.t.me/foo/9")
    assert channel == "foo"
    assert post_id == "9"


def test_validate_url_rejects_non_telegram():
    with pytest.raises(TelegramReaderError):
        validate_url("https://example.com/foo/1")


def test_validate_url_rejects_channel_root():
    # No post id — just t.me/<channel> — we can't fetch a single post.
    with pytest.raises(TelegramReaderError):
        validate_url("https://t.me/durov")


def test_validate_url_rejects_empty():
    with pytest.raises(TelegramReaderError):
        validate_url("")


# ── HTML parsing ────────────────────────────────────────────────────────────


def _fake_html(text: str = "Hello", author: str = "Some Channel") -> str:
    return f"""
    <html>
      <head>
        <meta property="og:description" content="OG: {text}">
      </head>
      <body>
        <div class="tgme_widget_message_author"><span dir="auto">{author}</span></div>
        <div class="tgme_widget_message_text js-message_text">
          {text}
        </div>
      </body>
    </html>
    """


def _fake_response(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        text=text,
        request=httpx.Request("GET", "https://t.me/foo/1?embed=1&single"),
    )


def test_fetch_post_extracts_message_text():
    html = _fake_html(text="Watch The Favourite tonight")
    with patch("backend.services.telegram_reader.httpx.get", return_value=_fake_response(html)):
        post = fetch_post("https://t.me/foo/1")
    assert post.channel == "foo"
    assert post.post_id == "1"
    assert "Watch The Favourite tonight" in post.text
    assert post.author == "Some Channel"


def test_fetch_post_handles_br_as_newlines():
    html = _fake_html(text="Line one<br>Line two<br/>Line three")
    with patch("backend.services.telegram_reader.httpx.get", return_value=_fake_response(html)):
        post = fetch_post("https://t.me/foo/1")
    assert "Line one" in post.text
    assert "Line three" in post.text
    # br -> newlines, not glued together
    assert "Line oneLine" not in post.text


def test_fetch_post_falls_back_to_og_description():
    html = """
    <html><head>
        <meta property="og:description" content="Pure caption">
    </head><body></body></html>
    """
    with patch("backend.services.telegram_reader.httpx.get", return_value=_fake_response(html)):
        post = fetch_post("https://t.me/foo/1")
    assert post.text == "Pure caption"


def test_fetch_post_404_raises_friendly_error():
    with patch("backend.services.telegram_reader.httpx.get", return_value=_fake_response("", 404)):
        with pytest.raises(TelegramReaderError) as exc:
            fetch_post("https://t.me/foo/1")
    assert "not found" in str(exc.value).lower()


def test_fetch_post_private_stub_raises():
    private_html = (
        '<html><body>'
        '<div class="tgme_page_additional">If you have Telegram, you can view and join</div>'
        '</body></html>'
    )
    with patch(
        "backend.services.telegram_reader.httpx.get",
        return_value=_fake_response(private_html),
    ):
        with pytest.raises(TelegramReaderError) as exc:
            fetch_post("https://t.me/private_chan/1")
    assert "private" in str(exc.value).lower()


def test_fetch_post_empty_post_raises():
    empty_html = "<html><body></body></html>"
    with patch(
        "backend.services.telegram_reader.httpx.get",
        return_value=_fake_response(empty_html),
    ):
        with pytest.raises(TelegramReaderError):
            fetch_post("https://t.me/foo/1")


def test_fetch_post_network_error_wrapped():
    def _boom(*_a, **_kw):
        raise httpx.ConnectError("boom")
    with patch("backend.services.telegram_reader.httpx.get", side_effect=_boom):
        with pytest.raises(TelegramReaderError) as exc:
            fetch_post("https://t.me/foo/1")
    assert "could not reach" in str(exc.value).lower()
