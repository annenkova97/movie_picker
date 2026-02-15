import base64
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yt_dlp
from openai import OpenAI

from backend.config import (
    OPENAI_API_KEY,
    INSTAGRAM_COOKIES_PATH,
    INSTAGRAM_VIDEO_DIR,
    INSTAGRAM_TEMP_DIR,
)
from backend.models.movie import MovieBase


REEL_URL_PATTERN = re.compile(
    r"https?://(www\.)?instagram\.com/(reel|reels)/[\w-]+/?",
)


SYSTEM_PROMPT = """\
You are a movie information extractor with web search. You receive a transcript \
and/or caption from an Instagram Reel that discusses one or more movies/films/series.

Your task: extract ALL movies mentioned and return a JSON array.

Each element must have exactly these fields:
- "title_ru": movie title in Russian
- "title_en": the official English title of the movie
- "description": a 1-2 sentence description of what the movie is about, in Russian

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


def _ensure_cookies_file() -> None:
    if not INSTAGRAM_COOKIES_PATH:
        raise InstagramReaderError("INSTAGRAM_COOKIES_PATH is not set")
    if not os.path.exists(INSTAGRAM_COOKIES_PATH):
        raise InstagramReaderError(
            "Cookie file not found. Set INSTAGRAM_COOKIES_PATH or place file at "
            f"{INSTAGRAM_COOKIES_PATH}"
        )


def download_reel(url: str) -> tuple[str, str]:
    _ensure_cookies_file()

    output_template = str(Path(INSTAGRAM_VIDEO_DIR) / "%(id)s.%(ext)s")
    ydl_opts: dict = {
        "outtmpl": output_template,
        "format": "mp4/best",
        "writeinfojson": True,
        "quiet": True,
        "no_warnings": True,
        "cookiefile": INSTAGRAM_COOKIES_PATH,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    video_id = info.get("id", "video")
    ext = info.get("ext", "mp4")
    video_path = str(Path(INSTAGRAM_VIDEO_DIR) / f"{video_id}.{ext}")

    caption = info.get("description", "") or ""

    json_path = Path(INSTAGRAM_VIDEO_DIR) / f"{video_id}.info.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if not caption:
                caption = meta.get("description", "") or ""
        finally:
            json_path.unlink(missing_ok=True)

    return video_path, caption


def extract_audio(video_path: str) -> str:
    audio_path = Path(INSTAGRAM_TEMP_DIR) / (Path(video_path).stem + ".mp3")

    subprocess.run(
        [
            "ffmpeg", "-y",
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
            "ffprobe",
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
                "ffmpeg", "-y",
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
