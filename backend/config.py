import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Public URL of the deployed Mini-App (Telegram web_app button target).
# Optional: when unset, the "Открыть в Lentochka" inline button after save
# is omitted, and users open the Mini-App via BotFather's menu button.
MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
JWT_EXPIRES_DAYS = int(os.getenv("JWT_EXPIRES_DAYS", "30"))
JWT_ALGORITHM = "HS256"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")   # Set on Railway for PostgreSQL
USE_POSTGRES = bool(DATABASE_URL)

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "data", "movies.db"),
)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
OMDB_BASE_URL = "http://www.omdbapi.com/"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
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

# Apify — Instagram парсится через их Instagram Scraper actor.
# Токен берётся в https://console.apify.com/settings/integrations
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
APIFY_INSTAGRAM_ACTOR = os.getenv(
    "APIFY_INSTAGRAM_ACTOR",
    # Reel-specific actor: даёт готовый transcript + кладёт видео в свой KVS,
    # так что нам не нужны Whisper и прямой download c Instagram CDN.
    "apify~instagram-reel-scraper",
)
