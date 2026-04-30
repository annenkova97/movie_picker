"""Public Telegram post parser via t.me embed view.

Telegram exposes a public, no-auth-required HTML preview for any post in a
public channel at ``https://t.me/<channel>/<id>?embed=1``. We fetch that page,
pull out the post text, and hand it off to the existing LLM movie-extraction
pipeline.

Limits:
- Only public channels work — private chats / +invite links return an empty
  page or a "join" stub.
- Image-only / sticker-only posts have no extractable text.
- Video posts: we only read the caption, not transcribe the video.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

import httpx


TELEGRAM_URL_PATTERN = re.compile(
    r"https?://(www\.)?t\.me/(?P<channel>[\w\d_]+)/(?P<post_id>\d+)/?",
)


# Strict regexes against the embed HTML. Telegram's embed markup has been
# stable for years; if it shifts we'll catch it via the parse test.
_OG_DESCRIPTION_RE = re.compile(
    r'<meta\s+property="og:description"\s+content="([^"]*)"',
    re.IGNORECASE,
)
_MESSAGE_TEXT_RE = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL,
)
_AUTHOR_RE = re.compile(
    r'<div class="tgme_widget_message_author[^"]*"[^>]*>.*?<span[^>]*>([^<]+)</span>',
    re.DOTALL,
)
# Privacy stub Telegram serves for private/non-existent channels.
_PRIVATE_STUB_MARKERS = (
    "tgme_page_additional",
    "If you have Telegram, you can view and join",
)


class TelegramReaderError(Exception):
    """Raised when a t.me URL can't be fetched or parsed into post text."""


@dataclass
class TelegramPost:
    url: str
    channel: str
    post_id: str
    text: str
    author: str | None


def validate_url(url: str) -> tuple[str, str, str]:
    """Return (canonical_url, channel, post_id) or raise TelegramReaderError."""
    match = TELEGRAM_URL_PATTERN.match(url.strip())
    if not match:
        raise TelegramReaderError(
            f"Invalid Telegram post URL: {url}\n"
            "Expected format: https://t.me/<channel>/<post_id>"
        )
    channel = match.group("channel")
    post_id = match.group("post_id")
    canonical = f"https://t.me/{channel}/{post_id}"
    return canonical, channel, post_id


def _strip_tags(fragment: str) -> str:
    """Best-effort HTML → plain text. Preserves line breaks from <br>."""
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    fragment = re.sub(r"</p>", "\n", fragment, flags=re.IGNORECASE)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def _looks_like_private(body: str) -> bool:
    return any(marker in body for marker in _PRIVATE_STUB_MARKERS) and "tgme_widget_message" not in body


def fetch_post(url: str, *, timeout: float = 15.0) -> TelegramPost:
    """Fetch a public t.me post and return its text. Synchronous, blocking."""
    canonical, channel, post_id = validate_url(url)
    embed_url = f"{canonical}?embed=1&single"

    try:
        resp = httpx.get(
            embed_url,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; LentochkaBot/1.0; +https://lentochka.app)"
                ),
            },
        )
    except httpx.HTTPError as exc:
        raise TelegramReaderError(f"Could not reach t.me: {exc}") from exc

    if resp.status_code == 404:
        raise TelegramReaderError(f"Post not found: {canonical}")
    if resp.status_code >= 400:
        raise TelegramReaderError(
            f"t.me returned HTTP {resp.status_code} for {canonical}"
        )

    body = resp.text

    if _looks_like_private(body):
        raise TelegramReaderError(
            "This post is in a private channel — open it in Telegram and copy the text manually."
        )

    text = ""
    msg_match = _MESSAGE_TEXT_RE.search(body)
    if msg_match:
        text = _strip_tags(msg_match.group(1))

    if not text:
        og_match = _OG_DESCRIPTION_RE.search(body)
        if og_match:
            text = html.unescape(og_match.group(1)).strip()

    if not text:
        raise TelegramReaderError(
            "Couldn't read the post — it may be empty, image-only, or restricted."
        )

    author = None
    author_match = _AUTHOR_RE.search(body)
    if author_match:
        author = html.unescape(author_match.group(1)).strip() or None

    return TelegramPost(
        url=canonical,
        channel=channel,
        post_id=post_id,
        text=text,
        author=author,
    )
