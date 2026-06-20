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

# Общий instagram-scraper — фолбэк, когда reel-specific actor не открывает рилс.
# Отдаёт caption (без готового transcript), читает часть «приватных» для
# reel-scraper'а ссылок.
APIFY_GENERAL_ACTOR = "apify~instagram-scraper"

APIFY_RUN_ENDPOINT = "https://api.apify.com/v2/acts/{actor}/runs"
APIFY_RUN_STATUS_ENDPOINT = "https://api.apify.com/v2/actor-runs/{run_id}"
APIFY_DATASET_ENDPOINT = "https://api.apify.com/v2/datasets/{dataset_id}/items"
APIFY_TIMEOUT_SECONDS = 240.0
APIFY_POLL_INTERVAL_SECONDS = 3.0

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


def _run_apify_actor(actor: str, payload: dict, *, label: str = "apify") -> dict:
    """Запускает Apify-actor и возвращает первый элемент его dataset'а."""
    items = _run_apify_actor_items(actor, payload, limit=1, label=label)
    return items[0]


def _run_apify_actor_items(
    actor: str, payload: dict, *, limit: int, label: str = "apify"
) -> list:
    """Запускает любой Apify-actor и возвращает элементы его dataset'а.

    Используем async flow вместо ``run-sync-get-dataset-items``:
    он держит TCP-соединение всё время работы actor'а (30-40 секунд) и
    регулярно обрывается на стороне Apify ``Server disconnected``.
    Поэтому: стартуем run, дёргаем статус каждые 3 секунды, потом
    читаем dataset. Каждый HTTP-вызов короткий и идемпотентный.

    Бросает ``InstagramReaderError`` на любой инфраструктурный сбой или если
    dataset пуст. Распознавание «actor отработал, но данных по ссылке нет»
    (error-запись в dataset'е) — на совести вызывающего, см. ``_is_error_item``.
    """
    _ensure_apify_token()

    # 1. Стартуем run
    try:
        start_resp = httpx.post(
            APIFY_RUN_ENDPOINT.format(actor=actor),
            params={"token": APIFY_TOKEN},
            json=payload,
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        raise InstagramReaderError(f"Apify run start failed: {exc}") from exc

    if start_resp.status_code >= 400:
        raise InstagramReaderError(
            f"Apify run start returned {start_resp.status_code}: {start_resp.text[:300]}"
        )

    run_data = (start_resp.json() or {}).get("data", {})
    run_id = run_data.get("id")
    dataset_id = run_data.get("defaultDatasetId")
    if not run_id or not dataset_id:
        raise InstagramReaderError("Apify did not return run/dataset id")

    # 2. Поллим статус, пока не закончится
    deadline = time.time() + APIFY_TIMEOUT_SECONDS
    status_url = APIFY_RUN_STATUS_ENDPOINT.format(run_id=run_id)
    final_status: str | None = None
    while time.time() < deadline:
        time.sleep(APIFY_POLL_INTERVAL_SECONDS)
        try:
            status_resp = httpx.get(
                status_url,
                params={"token": APIFY_TOKEN},
                timeout=15.0,
            )
        except httpx.HTTPError:
            # Транзитивная сетевая ошибка — просто продолжаем поллить
            continue
        if status_resp.status_code >= 400:
            continue
        final_status = ((status_resp.json() or {}).get("data") or {}).get("status")
        if final_status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    if final_status != "SUCCEEDED":
        raise InstagramReaderError(
            f"Apify run ({label}) finished with status: {final_status or 'timeout'}"
        )

    # 3. Читаем dataset (короткий запрос, без длинных hold-alive)
    try:
        items_resp = httpx.get(
            APIFY_DATASET_ENDPOINT.format(dataset_id=dataset_id),
            params={"token": APIFY_TOKEN, "limit": limit},
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        raise InstagramReaderError(f"Apify dataset fetch failed: {exc}") from exc

    if items_resp.status_code >= 400:
        raise InstagramReaderError(
            f"Apify dataset returned {items_resp.status_code}: {items_resp.text[:300]}"
        )

    try:
        items = items_resp.json()
    except ValueError as exc:
        raise InstagramReaderError(f"Apify returned non-JSON: {exc}") from exc

    if not isinstance(items, list) or not items:
        raise InstagramReaderError(
            "Apify не вернул данных для этой ссылки — проверь, что Reel публичный"
        )

    return items


def _is_error_item(item: dict) -> bool:
    """True, если actor вернул error-запись вместо данных.

    instagram-reel-scraper для недоступных рилзов кладёт в dataset
    ``{"error": "no_items", "errorDescription": "Empty or private data ..."}``.
    Раньше это молча принималось за «пустой пост» → бот говорил «не нашла
    фильмов», хотя на деле рилс просто не открылся.
    """
    return (
        isinstance(item, dict)
        and bool(item.get("error"))
        and not (item.get("caption") or item.get("transcript"))
    )


def _fetch_reel_text(url: str) -> tuple[str, str]:
    """reel-scraper ради готового транскрипта — БЕЗ скачивания видео.

    Видео ($0.02/МБ у этого актора) для извлечения названий не нужно, а
    транскрипт ($0.048 за начатую минуту) — дорогая ступень, поэтому её
    дёргаем только когда в подписи названия не нашлось. Возвращает
    ``(caption, transcript)``; ('', '') — на любой сбой или error-запись,
    это лишь одна ступень лесенки и ронять весь разбор она не должна.
    """
    try:
        item = _run_apify_actor(
            APIFY_INSTAGRAM_ACTOR,
            {
                # У этого актора поле называется "username", но принимает URL-ы рилзов.
                "username": [url],
                "resultsLimit": 1,
                # Apify сам прогонит аудио через свой транскрайбер — Whisper не нужен.
                "includeTranscript": True,
                # Видео НЕ качаем: для названий оно не нужно, а это главный расход.
                "includeDownloadedVideo": False,
            },
            label="reel-scraper-text",
        )
    except InstagramReaderError as exc:
        print(f"[instagram_reader] reel-scraper text failed: {exc}")
        return "", ""
    if _is_error_item(item):
        return "", ""
    return item.get("caption") or "", item.get("transcript") or ""


def _fetch_reel_video(url: str) -> str | None:
    """reel-scraper со скачиванием видео — только для vision-режима.

    Самая дорогая ступень ($0.02/МБ), поэтому вызывается последней и лишь
    когда явно запросили ``vision``. Качаем из Apify KeyValueStore (их IP,
    наш токен), а не с Instagram CDN — работает и с датацентровых IP.
    Возвращает путь к локальному .mp4 или ``None``.
    """
    try:
        item = _run_apify_actor(
            APIFY_INSTAGRAM_ACTOR,
            {
                "username": [url],
                "resultsLimit": 1,
                "includeTranscript": False,
                "includeDownloadedVideo": True,
            },
            label="reel-scraper-video",
        )
    except InstagramReaderError as exc:
        print(f"[instagram_reader] reel-scraper video failed: {exc}")
        return None
    if _is_error_item(item):
        return None

    apify_video_url = item.get("downloadedVideo")
    if not apify_video_url:
        return None
    short = item.get("shortCode") or _shortcode_from_url(url)
    dest = Path(INSTAGRAM_VIDEO_DIR) / f"{short}.mp4"
    try:
        _download_from_apify_kvs(apify_video_url, dest)
        return str(dest)
    except InstagramReaderError as exc:
        print(f"[instagram_reader] Apify KVS download failed: {exc}")
        return None


def _caption_via_general_scraper(url: str) -> str:
    """Фолбэк: общий apify/instagram-scraper. Достаёт caption там, где
    reel-scraper спотыкается (часть рилзов он отдаёт как «Empty or private»).

    Готового transcript у него нет — только подпись, но для рилзов-рекомендаций
    название обычно в подписи. Возвращает '' на любую ошибку: фолбэк не должен
    ронять весь разбор, дальше ``download_reel`` отдаст честную ошибку.
    """
    try:
        item = _run_apify_actor(
            APIFY_GENERAL_ACTOR,
            {
                "directUrls": [url],
                "resultsType": "posts",
                "resultsLimit": 1,
                "addParentData": False,
            },
            label="instagram-scraper",
        )
    except InstagramReaderError as exc:
        print(f"[instagram_reader] general scraper failed: {exc}")
        return ""

    if _is_error_item(item):
        return ""
    return item.get("caption") or ""


def fetch_top_comments(url: str, *, max_comments: int = 10) -> str:
    """Самые залайканные комментарии к Reel — текстом, по одному в строке.

    Фолбэк на случай, когда из озвучки и подписи название фильма не вытащить:
    под вирусными рилзами кто-то почти всегда пишет, что это за фильм, и такие
    комментарии собирают лайки. Возвращает '' на любую ошибку — это лишь одна
    ступень лесенки ``parse_reel_movies`` и ронять весь разбор она не должна.
    """
    try:
        items = _run_apify_actor_items(
            APIFY_GENERAL_ACTOR,
            {
                "directUrls": [url],
                "resultsType": "comments",
                "resultsLimit": 50,
                "addParentData": False,
            },
            limit=50,
            label="instagram-comments",
        )
    except InstagramReaderError as exc:
        print(f"[instagram_reader] comments fetch failed: {exc}")
        return ""

    comments = []
    for item in items:
        if not isinstance(item, dict) or _is_error_item(item):
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        likes = item.get("likesCount") or 0
        comments.append((likes, text))

    comments.sort(key=lambda c: c[0], reverse=True)
    lines = [f"- {text} ({likes} likes)" for likes, text in comments[:max_comments]]
    return "\n".join(lines)


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


def _download_from_apify_kvs(kvs_url: str, dest_path: Path) -> None:
    """Качает файл из Apify KeyValueStore — обычная REST-ручка + наш токен.

    URL формата ``https://api.apify.com/v2/key-value-stores/{id}/records/{key}``
    приходит в поле ``downloadedVideo`` от instagram-reel-scraper.
    """
    try:
        with httpx.stream(
            "GET",
            kvs_url,
            params={"token": APIFY_TOKEN},
            timeout=120.0,
            follow_redirects=True,
        ) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
    except httpx.HTTPError as exc:
        raise InstagramReaderError(f"Не удалось скачать видео из Apify KVS: {exc}") from exc


# ── Кэш разбора по shortcode ──────────────────────────────────────────────────
# Один и тот же рилс (особенно вирусный) присылают многократно — разными
# людьми или повторно. Контент рилза неизменен, разбор детерминирован, так что
# платить Apify за него повторно незачем. Держим результат сутки, с грубым
# вытеснением самого старого при переполнении.
PARSE_CACHE_TTL_SECONDS = 24 * 3600
PARSE_CACHE_MAX_ENTRIES = 512
_ParseResult = tuple[list["MovieInfo"], str, str]
_parse_cache: dict[str, tuple[float, _ParseResult]] = {}


def _parse_cache_get(shortcode: str) -> _ParseResult | None:
    entry = _parse_cache.get(shortcode)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > PARSE_CACHE_TTL_SECONDS:
        _parse_cache.pop(shortcode, None)
        return None
    return value


def _parse_cache_put(shortcode: str, value: _ParseResult) -> _ParseResult:
    if shortcode not in _parse_cache and len(_parse_cache) >= PARSE_CACHE_MAX_ENTRIES:
        oldest = min(_parse_cache, key=lambda k: _parse_cache[k][0])
        _parse_cache.pop(oldest, None)
    _parse_cache[shortcode] = (time.time(), value)
    return value


def clear_parse_cache() -> None:
    """Сбросить кэш разбора (используется в тестах)."""
    _parse_cache.clear()


def parse_reel_movies(
    url: str, *, vision: bool = False
) -> tuple[list[MovieInfo], str, str]:
    """Извлекает фильмы из Reel по caption-first лесенке. Главная точка входа.

    Возвращает ``(movies, caption, transcript)``. Тратим Apify-кредиты
    ступенчато, от дешёвого к дорогому, и останавливаемся на первом найденном
    фильме — потому что у рилзов-рекомендаций название почти всегда уже в
    подписи, и тогда ни видео, ни транскрипт, ни комментарии не нужны:

      1. подпись через общий instagram-scraper — без видео и транскрипта;
      2. транскрипт через reel-scraper, но БЕЗ скачивания видео — только если
         в подписи названия не нашлось;
      3. топ-комментарии — если и в озвучке названия нет (под вирусными рилзами
         фильм почти всегда называют зрители);
      4. кадры видео (vision) — только при ``vision=True`` и только если до сюда
         ничего не нашли.

    Результат кэшируется по shortcode (``PARSE_CACHE_TTL_SECONDS``), так что
    повторный разбор того же рилза не стоит ничего. Бросает
    ``InstagramReaderError``, если рилс вообще не открылся — ни подписи, ни
    озвучки, — а не делает вид, что в посте просто нет фильмов.
    """
    _ensure_apify_token()

    shortcode = _shortcode_from_url(url)
    cached = _parse_cache_get(shortcode)
    if cached is not None:
        print(f"[instagram_reader] parse cache hit for {shortcode}")
        return cached

    # 1. Дешёвая подпись — общий scraper, без видео и транскрипта.
    general_caption = _caption_via_general_scraper(url)
    caption = general_caption
    transcript = ""
    movies = extract_movies("", caption) if caption.strip() else []
    if movies:
        return _parse_cache_put(shortcode, (movies, caption, transcript))

    # 2. Транскрипт — reel-scraper БЕЗ скачивания видео.
    rs_caption, transcript = _fetch_reel_text(url)
    if not caption.strip():
        caption = rs_caption

    if not caption.strip() and not transcript.strip():
        # Ни подписи, ни озвучки — рилс не открылся. Не кэшируем: сбой может
        # быть транзитивным (Apify «Empty or private»), пусть ретраят.
        raise InstagramReaderError(
            "Не удалось открыть этот Reel — возможно, он приватный или "
            "недоступен. Попробуй другую ссылку."
        )

    # Перезапускаем извлечение только если появился новый текст: транскрипт
    # либо подпись от reel-scraper (когда у общего её не было). Иначе это был
    # бы повторный LLM-вызов по тем же данным.
    if transcript.strip() or (not general_caption.strip() and caption.strip()):
        movies = extract_movies(transcript, caption)
        if movies:
            return _parse_cache_put(shortcode, (movies, caption, transcript))

    # 3. Комментарии — под вирусными рилзами название часто пишут зрители.
    comments = fetch_top_comments(url)
    if comments:
        movies = extract_movies(transcript, caption, comments=comments)
        if movies:
            return _parse_cache_put(shortcode, (movies, caption, transcript))

    # 4. Vision по кадрам — только если явно попросили (бэкенд, payload.vision).
    if vision:
        video_path = _fetch_reel_video(url)
        if video_path:
            frames = extract_frames(video_path, 3)
            try:
                movies = extract_movies(transcript, caption, frames, True, comments)
            finally:
                cleanup_temp_files(frames)

    # Рилс открылся, но фильма не нашли — результат детерминирован, кэшируем,
    # чтобы повторная присылка того же рилза не стоила ничего.
    return _parse_cache_put(shortcode, (movies, caption, transcript))


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
    comments: str = "",
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
    if comments:
        # Комментарии зрителей — фолбэк, когда в озвучке/подписи названия нет:
        # обычно кто-то называет фильм, и такой коммент собирает лайки.
        text += (
            "Top viewer comments (viewers often name the movie here; "
            "trust highly-liked comments):\n"
            f"{comments}\n\n"
        )
    # Допускаем vision-only режим: пост может быть с одной фоткой постера/кадра
    # без текста — пусть модель опирается на изображение.
    if not text.strip() and not use_vision_model:
        return []

    if use_vision_model:
        prompt_text = text or (
            "No transcript or caption was provided. Identify the movie(s) from "
            "the image(s) alone — poster, screenshot, scene, or actors."
        )
        user_content: list[dict] = [{"type": "text", "text": prompt_text}]
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
