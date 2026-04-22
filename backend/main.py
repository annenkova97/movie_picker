from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend import database as db
from backend.routers import movies, search, recommend, instagram, awards
from backend.services.awards_seed import sync_awards_catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при запуске приложения"""
    # Создаём директорию data если её нет
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Инициализируем базу данных
    await db.init_db()
    print("База данных инициализирована")

    # Догружаем каталог наград (идемпотентно)
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

# CORS для локальной разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры API
app.include_router(movies.router)
app.include_router(search.router)
app.include_router(recommend.router)
app.include_router(instagram.router)
app.include_router(awards.router)

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


@app.get("/api/health")
async def health_check():
    """Проверка работоспособности API"""
    return {"status": "ok"}
