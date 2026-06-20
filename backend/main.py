import asyncio
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

# Sentry инициализируем до создания приложения, чтобы ловить и ошибки старта.
# Без DSN (локалка, тесты) — полностью выключен, импорт не выполняется.
if config.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        # Ошибки — все; перфоманс-трейсы не нужны на friends-бете.
        traces_sample_rate=0.0,
        send_default_pii=False,
    )
    print("[sentry] enabled", flush=True)
from backend.rate_limit import limiter
from backend.routers import movies, search, recommend, instagram, awards, auth, health, telegram, shares, books, telegram_webhook, availability, settings as settings_router, events
from backend.services.awards_seed import (
    sync_awards_catalog,
    backfill_media_type,
    backfill_runtime,
)


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

    # Разовый бэкфилл media_type у старых записей (фильм/сериал). Гоняем в фоне,
    # чтобы не задерживать старт и health-check; внутри гейт по app_meta — пройдёт
    # один раз. SKIP_AWARDS_SEED=1 заодно отключает и его в тестах.
    if os.getenv("SKIP_AWARDS_SEED") != "1":
        async def _run_media_type_backfill():
            try:
                await backfill_media_type()
            except Exception as exc:
                print(f"[media_type] бэкфилл упал: {exc}", flush=True)
            # Длительности — после классификации, тем же фоновым проходом.
            try:
                await backfill_runtime()
            except Exception as exc:
                print(f"[runtime] бэкфилл упал: {exc}", flush=True)

        app.state.media_type_task = asyncio.create_task(_run_media_type_backfill())

    # Telegram-бот через webhook в этом же процессе. Включается только когда
    # заданы токен + публичный URL + секрет. Локально — пусто, бот гоняется
    # отдельно через `python bot.py` (long-polling).
    app.state.bot_app = None
    if (
        config.TELEGRAM_BOT_TOKEN
        and config.PUBLIC_BASE_URL
        and config.TELEGRAM_WEBHOOK_SECRET
    ):
        try:
            from bot_setup import build_application
            bot_app = build_application()
            await bot_app.initialize()
            await bot_app.start()
            webhook_url = (
                f"{config.PUBLIC_BASE_URL}/telegram/webhook/"
                f"{config.TELEGRAM_WEBHOOK_SECRET}"
            )
            await bot_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            app.state.bot_app = bot_app
            print(f"[bot] webhook set: {webhook_url}", flush=True)
        except Exception as exc:
            print(f"[bot] failed to start webhook bot: {exc}", flush=True)

    yield

    if getattr(app.state, "bot_app", None) is not None:
        try:
            await app.state.bot_app.stop()
            await app.state.bot_app.shutdown()
        except Exception as exc:
            print(f"[bot] shutdown error: {exc}", flush=True)
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
app.include_router(books.router)
app.include_router(telegram_webhook.router)
app.include_router(availability.router)
app.include_router(settings_router.router)
app.include_router(events.router)
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


