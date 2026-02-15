import os
from dotenv import load_dotenv

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.db")
OMDB_BASE_URL = "http://www.omdbapi.com/"

# Instagram
INSTAGRAM_COOKIES_FILE = os.getenv("INSTAGRAM_COOKIES_FILE", "")
INSTAGRAM_VIDEOS_DIR = os.path.join(os.path.dirname(__file__), "data", "videos")
INSTAGRAM_TEMP_DIR = os.path.join(os.path.dirname(__file__), "data", "tmp")
