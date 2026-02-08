#!/usr/bin/env python3
"""Скрипт запуска приложения Movie Picker"""

import os
import sys

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    # Проверяем наличие .env файла
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env_example_path = os.path.join(os.path.dirname(__file__), ".env.example")

    if not os.path.exists(env_path):
        print("=" * 50)
        print("ВНИМАНИЕ: Файл .env не найден!")
        print("=" * 50)
        print("\nСкопируйте .env.example в .env и добавьте API ключи:")
        print(f"  cp {env_example_path} {env_path}")
        print("\nНеобходимые ключи:")
        print("  - OMDB_API_KEY: получить на http://www.omdbapi.com/apikey.aspx")
        print("  - ANTHROPIC_API_KEY: получить на https://console.anthropic.com/")
        print("=" * 50)
        sys.exit(1)

    print("=" * 50)
    print("Movie Picker")
    print("=" * 50)
    print("\nЗапуск сервера...")
    print("Откройте в браузере: http://localhost:8000")
    print("API документация: http://localhost:8000/docs")
    print("\nДля остановки нажмите Ctrl+C")
    print("=" * 50)

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
