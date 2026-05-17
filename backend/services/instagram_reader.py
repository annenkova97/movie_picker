from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from openai import OpenAI

from backend.config import (
    OPENAI_API_KEY,
    APIFY_TOKEN,
    APIFY_INSTAGRAM_ACTOR,
    INSTAGRAM_VIDEO_DIR,
    INSTAGRAM_TEMP_DIR,
)
from backend.models.movie import MovieBase


def _find_bin(name: str) -> str:
    """Find binary in PATH or common Homebrew locations."""
    path = shutil.which(name)
    if path:
        return path
    for candidate in [f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}"]:
        if os.path.isfile(candidate):
            return candidate
    return name


FFMPEG = _find_bin("ffmpeg")
FFPROBE = _find_bin("ffprobe")

REEL_URL_PATTERN = re.compile(
    r"https?://(www\.)?instagram\.com/(reel|reels)/[\w-]+/?",
)

APIFY_SYNC_ENDPOINT = (
    "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
)
APIFY_TIMEOUT_SECONDS = 180.0

# Instagram CDN иногда рвёт TLS-соединение посреди тела ответа.
# Браузерный UA и ретраи лечат это в ~99% случаев.
CDN_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)
CDN_DOWNLOAD_ATTEMPTS = 3


SYSTEM_PROMPT = """\
You are a movie information extractor with web search. You receive a transcript \
and/or caption from an Instagram Reel that discusses one or more movies/films/series.

Your task: extract ALL movies mentioned and return a JSON array.

Each element must have exactly these fields:
- "title_ru": movie title in Russian
- "title_en": the official English title of the movie
- "description": a 1-2 sentence description of what the movie is about, in Russian
- "quote": a short compelling quote from the transcript (1-2 sentences, in Russian) \
explaining why this movie is worth watching. If the speaker said something interesting \
about the movie, capture that. If nothing compelling was said, use an empty string.

Rules:
- "title_en" MUST be the real official English title as listed on IMDb. \
Search the web to verify the correct English title for every movie. \
Do NOT translate the Russian title literally and do NOT guess.
- For well-known films use the correct English title \
(e.g. «Бедные-несчастные» = "Poor Things", «Фаворитка» = "The Favourite").
- For NEW or unknown movies, search the web to find the official English title. \
For example: «Фэкхем-Холл» → search "Фэкхем-Холл фильм 2025 english title" \
→ find "The Amateur". NEVER transliterate if the real title can be found.
- The Reel may discuss a NEW upcoming movie. Pay close attention to context: \
if the caption says "новая" / "новый фильм" / "скоро", the main subject is that \
new movie, not previously released films mentioned for comparison.
- If only one language title is available, search for the counterpart.
- If no movies are found, return an empty array: []
- Return ONLY valid JSON, no markdown, no extra text.
"""


@dataclass
class MovieInfo:
    title_ru: str
    title_en: str
    description: str
    quote: str = ""


class InstagramReaderError(Exception):
    pass


def validate_url(url: str) -> str:
    match = REEL_URL_PATTERN.match(url.strip())
    if not match:
        raise InstagramReaderError(
            f"Invalid Instagram Reel URL: {url}\n"
            "Expected format: https://www.instagram.com/reel/ABC123/"
        )
    return url.strip()


def _ensure_apify_token() -> None:
    if not APIFY_TOKEN:
        raise InstagramReaderError(
            "APIFY_TOKEN is not set. Get one at "
            "https://console.apify.com/settings/integrations"
        )


def _shortcode_from_url(url: str) -> str:
    """Извлекает shortcode рилза из URL — используется как имя файла."""
    match = re.search(r"/(reel|reels|p)/([\w-]+)", url)
    if match:
        return match.group(2)
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:11]


def _call_apify_instagram(url: str) -> dict:
    """Запускает Apify Instagram Scraper и возвращает первый результат.

    Используем синхронный endpoint ``run-sync-get-dataset-items`` —
    он держит соединение пока actor работает и сразу отдаёт распарсенный JSON.
    """
    _ensure_apify_token()

    endpoint = APIFY_SYNC_ENDPOINT.format(actor=APIFY_INSTAGRAM_ACTOR)
    payload = {
        "directUrls": [url],
        "resultsType": "details",
        "resultsLimit": 1,
        "addParentData": False,
    }

    try:
        response = httpx.post(
            endpoint,
            params={"token": APIFY_TOKEN},
            json=payload,
            timeout=APIFY_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise InstagramReaderError(f"Apify request failed: {exc}") from exc

    if response.status_code >= 400:
        raise InstagramReaderError(
            f"Apify returned {response.status_code}: {response.text[:300]}"
        )

    try:
        items = response.json()
    except ValueError as exc:
        raise InstagramReaderError(f"Apify returned non-JSON: {exc}") from exc

    if not isinstance(items, list) or not items:
        raise InstagramReaderError(
            "Apify не вернул данных для этой ссылки — проверь, что Reel публичный"
        )

    return items[0]


def _download_video(video_url: str, dest_path: Path) -> None:
    """Качаем .mp4 с Instagram CDN — куки не нужны, ссылка подписанная.

    Instagram CDN периодически роняет TLS-соединение на середине ответа
    (видно как ``SSL: UNEXPECTED_EOF_WHILE_READING``). Делаем несколько
    попыток с экспоненциальным бэкоффом — подписанная ссылка из Apify
    обычно живёт достаточно долго, чтобы пережить 2-3 ретрая.
    """
    headers = {"User-Agent": CDN_USER_AGENT}
    last_exc: Exception | None = None

    for attempt in range(1, CDN_DOWNLOAD_ATTEMPTS + 1):
        try:
            with httpx.stream(
                "GET",
                video_url,
                timeout=60.0,
                follow_redirects=True,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                        f.write(chunk)
            return
        except httpx.HTTPError as exc:
            last_exc = exc
            # Удаляем недоскачанный мусор, чтобы при ретрае писать с нуля
            try:
                dest_path.unlink(missing_ok=True)
            except OSError:
                pass
            if attempt < CDN_DOWNLOAD_ATTEMPTS:
                time.sleep(1.5 * attempt)

    raise InstagramReaderError(
        f"Не удалось скачать видео с CDN за {CDN_DOWNLOAD_ATTEMPTS} попытки: {last_exc}"
    ) from last_exc


def download_reel(url: str) -> tuple[str, str]:
    """Парсит Reel через Apify, скачивает видео, возвращает (video_path, caption).

    Интерфейс совместим с прежней yt-dlp-реализацией, чтобы вызывающий код
    в ``backend/routers/instagram.py`` не менялся.
    """
    item = _call_apify_instagram(url)

    caption = item.get("caption") or ""
    video_url = item.get("videoUrl") or item.get("video_url")

    if not video_url:
        raise InstagramReaderError(
            "В ответе Apify нет ссылки на видео — возможно, это не Reel, "
            "а фото-пост"
        )

    short = item.get("shortCode") or _shortcode_from_url(url)
    video_path = Path(INSTAGRAM_VIDEO_DIR) / f"{short}.mp4"
    _download_video(video_url, video_path)

    return str(video_path), caption


def extract_audio(video_path: str) -> str:
    audio_path = Path(INSTAGRAM_TEMP_DIR) / (Path(video_path).stem + ".mp3")

    subprocess.run(
        [
            FFMPEG, "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "64k",
            "-ar", "16000",
            "-ac", "1",
            str(audio_path),
        ],
        capture_output=True,
        check=True,
    )

    return str(audio_path)


def extract_frames(video_path: str, count: int = 3) -> list[str]:
    result = subprocess.run(
        [
            FFPROBE,
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(result.stdout.strip())

    frame_paths: list[str] = []
    for i in range(count):
        timestamp = duration * (i + 1) / (count + 1)
        frame_path = Path(INSTAGRAM_TEMP_DIR) / f"frame_{i}.jpg"

        subprocess.run(
            [
                FFMPEG, "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                str(frame_path),
            ],
            capture_output=True,
            check=True,
        )
        frame_paths.append(str(frame_path))

    return frame_paths


def transcribe(audio_path: str) -> str:
    if not OPENAI_API_KEY:
        raise InstagramReaderError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=OPENAI_API_KEY)

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

    return response.text


def extract_movies(
    transcript: str,
    caption: str,
    frame_paths: list[str] | None = None,
    use_vision: bool = False,
) -> list[MovieInfo]:
    if not OPENAI_API_KEY:
        raise InstagramReaderError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=OPENAI_API_KEY)

    use_vision_model = use_vision and frame_paths

    text = ""
    if transcript:
        text += f"Transcript:\n{transcript}\n\n"
    if caption:
        text += f"Caption:\n{caption}\n\n"
    if not text.strip():
        return []

    if use_vision_model:
        user_content: list[dict] = [{"type": "text", "text": text}]
        for path in frame_paths:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
    else:
        response = client.chat.completions.create(
            model="gpt-4o-mini-search-preview",
            web_search_options={"search_context_size": "low"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )

    raw = response.choices[0].message.content or "[]"
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    # Search model may wrap JSON in explanatory text; extract JSON array
    json_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try fixing common LLM JSON issues (trailing commas, extra braces)
        try:
            fixed = re.sub(r",\s*([}\]])", r"\1", raw)
            data = json.loads(fixed)
        except json.JSONDecodeError:
            print(f"[extract_movies] JSON parse failed for: {raw[:300]}")
            return []

    if not isinstance(data, list):
        data = [data]

    movies: list[MovieInfo] = []
    for item in data:
        if isinstance(item, dict) and "title_en" in item:
            movies.append(
                MovieInfo(
                    title_ru=item.get("title_ru", ""),
                    title_en=item.get("title_en", ""),
                    description=item.get("description", ""),
                    quote=item.get("quote", ""),
                )
            )

    return movies


def movieinfo_to_moviebase(movie: MovieInfo) -> MovieBase:
    title = movie.title_ru or movie.title_en
    original_title = movie.title_en if movie.title_ru else None
    raw_key = f"{movie.title_en}|{movie.title_ru}".encode("utf-8")
    imdb_id = "insta_" + hashlib.sha1(raw_key).hexdigest()[:16]

    return MovieBase(
        imdb_id=imdb_id,
        title=title,
        original_title=original_title,
        year=None,
        genres=[],
        description=movie.description,
        plot=None,
        cast=[],
        director=None,
        poster_url=None,
        imdb_rating=None,
        awards=None,
    )


def cleanup_temp_files(paths: list[str]) -> None:
    for path in paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
