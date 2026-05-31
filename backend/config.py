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

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. Generate one with `openssl rand -hex 32` and put "
        "it in .env (locally) or the Railway env vars (prod). Раньше тут был "
        "хардкод-дефолт — это значило, что любой мог подделать токены известным "
        "ключом, поэтому теперь старт без секрета намеренно падает."
    )
JWT_EXPIRES_DAYS = int(os.getenv("JWT_EXPIRES_DAYS", "30"))
JWT_ALGORITHM = "HS256"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")   # Set on Railway for PostgreSQL
USE_POSTGRES = bool(DATABASE_URL)

# Список origin'ов, которым разрешён CORS. Запятая как разделитель.
# Локально достаточно дефолта; на проде указать домен фронта через
# CORS_ALLOW_ORIGINS, напр. "https://lentochka.up.railway.app".
_cors_raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://localhost:8000")
CORS_ALLOW_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "data", "movies.db"),
)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
OMDB_BASE_URL = "http://www.omdbapi.com/"

# TMDB используется как русскоязычный поисковик: OMDB кириллицу не понимает.
# Ключ бесплатный, выдаётся в настройках профиля на themoviedb.org → API.
# Если не задан — пайплайн откатывается на OMDB + LLM-перевод названия.
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

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
