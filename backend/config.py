import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.db")
OMDB_BASE_URL = "http://www.omdbapi.com/"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INSTAGRAM_COOKIES_PATH = os.getenv(
    "INSTAGRAM_COOKIES_PATH",
    os.path.join(DATA_DIR, "instagram_cookies.txt")
)
INSTAGRAM_VIDEO_DIR = os.getenv(
    "INSTAGRAM_VIDEO_DIR",
    os.path.join(DATA_DIR, "instagram_videos")
)
INSTAGRAM_TEMP_DIR = os.getenv(
    "INSTAGRAM_TEMP_DIR",
    os.path.join(DATA_DIR, "instagram_tmp")
)

os.makedirs(INSTAGRAM_VIDEO_DIR, exist_ok=True)
os.makedirs(INSTAGRAM_TEMP_DIR, exist_ok=True)
