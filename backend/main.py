from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend import config
from backend import database as db
from backend.rate_limit import limiter
from backend.routers import movies, search, recommend, instagram, awards, auth, health, telegram, shares
from backend.services.awards_seed import sync_awards_catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при запуске приложения"""
    # Создаём директорию data если её нет
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Инициализируем базу данных
    engine = "PostgreSQL" if config.USE_POSTGRES else f"SQLite ({config.DATABASE_PATH})"
    print(f"[db] Using {engine}", flush=True)
    await db.init_db()
    print("[db] init_db OK", flush=True)

    # Догружаем каталог наград (идемпотентно). SKIP_AWARDS_SEED=1 — для тестов.
    if os.getenv("SKIP_AWARDS_SEED") != "1":
        try:
            await sync_awards_catalog()
        except Exception as exc:
            print(f"Не удалось синхронизировать каталог наград: {exc}")

    yield

    # Cleanup при остановке (если нужно)
    print("Приложение остановлено")


app = FastAPI(
    title="Movie Picker",
    description="Приложение для выбора фильмов с рекомендациями на основе AI",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiting (slowapi): лимитер в app.state, обработчик 429 и middleware,
# который проставляет заголовки X-RateLimit-* в ответах.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS прибит к конкретным origin'ам (см. CORS_ALLOW_ORIGINS в config).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры API
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(search.router)
app.include_router(recommend.router)
app.include_router(instagram.router)
app.include_router(telegram.router)
app.include_router(awards.router)
app.include_router(shares.router)
app.include_router(health.router)

# Статические файлы frontend (собранный Vite-бандл)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
assets_path = os.path.join(frontend_path, "assets")
favicon_path = os.path.join(frontend_path, "favicon.svg")

if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
if os.path.exists(frontend_path):
    # Обратно совместимый путь для старых ссылок на /static/*
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/favicon.svg")
async def favicon():
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    return FileResponse(os.path.join(frontend_path, "favicon.ico")) if os.path.exists(os.path.join(frontend_path, "favicon.ico")) else {"detail": "not found"}


@app.get("/")
async def root():
    """Главная страница — отдаём frontend"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return {"message": "Movie Picker API", "docs": "/docs"}


