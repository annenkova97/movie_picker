"""Instagram Reel processing: download → transcribe → extract movies."""

import re
import json
import base64
import shutil
import subprocess
from pathlib import Path

import yt_dlp
from openai import OpenAI

from backend.config import OPENAI_API_KEY, INSTAGRAM_COOKIES_FILE, INSTAGRAM_VIDEOS_DIR, INSTAGRAM_TEMP_DIR

REEL_URL_PATTERN = re.compile(
    r"https?://(www\.)?instagram\.com/(reel|reels)/[\w-]+/?",
)

EXTRACT_PROMPT = """\
You are a movie information extractor. You receive a transcript and/or caption \
from an Instagram Reel that discusses one or more movies/films/series.

Your task: extract ALL movies mentioned and return a JSON array.

Each element must have exactly these fields:
- "title_ru": movie title in Russian
- "title_en": movie title in English
- "description": a 1-2 sentence description of what the movie is about, in Russian

Rules:
- If only one language title is available, translate it yourself.
- If no movies are found, return an empty array: []
- Return ONLY valid JSON, no markdown, no extra text.
"""


def validate_url(url: str) -> str:
    match = REEL_URL_PATTERN.match(url)
    if not match:
        raise ValueError(
            f"Invalid Instagram Reel URL: {url}\n"
            "Expected format: https://www.instagram.com/reel/ABC123/"
        )
    return url.strip()


def _ensure_dirs():
    Path(INSTAGRAM_VIDEOS_DIR).mkdir(parents=True, exist_ok=True)
    Path(INSTAGRAM_TEMP_DIR).mkdir(parents=True, exist_ok=True)


def download_reel(url: str) -> tuple[str, str]:
    """Download Reel video and extract caption.

    Returns (video_path, caption). Video is saved permanently in videos dir.
    """
    _ensure_dirs()
    tmp = Path(INSTAGRAM_TEMP_DIR)
    output_template = str(tmp / "%(id)s.%(ext)s")

    ydl_opts: dict = {
        "outtmpl": output_template,
        "format": "mp4/best",
        "quiet": True,
        "no_warnings": True,
    }

    if INSTAGRAM_COOKIES_FILE:
        ydl_opts["cookiefile"] = INSTAGRAM_COOKIES_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    video_id = info.get("id", "video")
    ext = info.get("ext", "mp4")
    tmp_video = tmp / f"{video_id}.{ext}"
    caption = info.get("description", "") or ""

    # Move video to permanent storage
    dest = Path(INSTAGRAM_VIDEOS_DIR) / f"{video_id}.{ext}"
    shutil.move(str(tmp_video), str(dest))

    return str(dest), caption


def extract_audio(video_path: str) -> str:
    """Extract MP3 audio (64kbps, 16kHz) for Whisper."""
    audio_path = Path(INSTAGRAM_TEMP_DIR) / (Path(video_path).stem + ".mp3")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "libmp3lame",
            "-ab", "64k", "-ar", "16000", "-ac", "1",
            str(audio_path),
        ],
        capture_output=True, check=True,
    )
    return str(audio_path)


def extract_frames(video_path: str, count: int = 3) -> list[str]:
    """Extract evenly spaced frames for vision analysis."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True, text=True, check=True,
    )
    duration = float(result.stdout.strip())

    paths: list[str] = []
    for i in range(count):
        timestamp = duration * (i + 1) / (count + 1)
        frame_path = Path(INSTAGRAM_TEMP_DIR) / f"frame_{i}.jpg"
        subprocess.run(
            [
                "ffmpeg", "-y", "-ss", str(timestamp),
                "-i", video_path, "-vframes", "1", "-q:v", "2",
                str(frame_path),
            ],
            capture_output=True, check=True,
        )
        paths.append(str(frame_path))
    return paths


def transcribe(audio_path: str) -> str:
    """Transcribe audio via OpenAI Whisper API."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(model="whisper-1", file=f)
    return response.text


def extract_movies(
    transcript: str,
    caption: str,
    frame_paths: list[str] | None = None,
    use_vision: bool = False,
) -> list[dict]:
    """Extract movie info via GPT. Returns list of dicts with title_ru, title_en, description."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    model = "gpt-4o" if use_vision and frame_paths else "gpt-4o-mini"

    user_content: list[dict] = []

    text = ""
    if transcript:
        text += f"Transcript:\n{transcript}\n\n"
    if caption:
        text += f"Caption:\n{caption}\n\n"
    if not text.strip():
        return []

    user_content.append({"type": "text", "text": text})

    if use_vision and frame_paths:
        for path in frame_paths:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content or "[]"
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        data = [data]

    return [
        item for item in data
        if isinstance(item, dict) and "title_en" in item
    ]


def cleanup_temp():
    """Remove temp files but keep saved videos."""
    tmp = Path(INSTAGRAM_TEMP_DIR)
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)


def process_reel(url: str, use_vision: bool = False) -> list[dict]:
    """Full pipeline: download → transcribe → extract movies.

    Returns list of dicts: [{title_ru, title_en, description}, ...]
    """
    try:
        url = validate_url(url)
        video_path, caption = download_reel(url)
        audio_path = extract_audio(video_path)

        frame_paths = None
        if use_vision:
            frame_paths = extract_frames(video_path, count=3)

        transcript = transcribe(audio_path)
        movies = extract_movies(transcript, caption, frame_paths, use_vision)
        return movies
    finally:
        cleanup_temp()
