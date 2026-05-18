"""One-time helper для переезда библиотеки с email-аккаунта на Telegram-аккаунт.

Контекст: исторически юзер логинился по email и накопил фильмы. После добавления
бота в Telegram стал заходить через Mini App — бэкенд создал ему синтетический
``tg<id>@tg.example.com`` аккаунт с пустой полкой. Скрипт сливает их в один.

Запуск (DATABASE_URL — Postgres-строка из Railway):

    DATABASE_URL='postgresql://...' python scripts/migrate_to_telegram.py

Или для локальной SQLite-БД:

    python scripts/migrate_to_telegram.py

Скрипт интерактивный — покажет всех юзеров и спросит source/target.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Импортируем модули проекта.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import database as db


async def list_users() -> list[dict]:
    """Возвращает всех юзеров с числом фильмов на полке."""
    if os.environ.get("DATABASE_URL"):
        from backend import db_postgres
        async with db_postgres._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT u.id, u.email, u.telegram_id, u.name, "
                "  (SELECT COUNT(*) FROM movies m WHERE m.user_id = u.id AND m.in_library=true) AS movies "
                "FROM users u ORDER BY u.id"
            )
            return [dict(r) for r in rows]
    import aiosqlite
    from backend.config import DATABASE_PATH
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        async with conn.execute(
            "SELECT u.id, u.email, u.telegram_id, u.name, "
            "  (SELECT COUNT(*) FROM movies m WHERE m.user_id = u.id AND m.in_library=1) AS movies "
            "FROM users u ORDER BY u.id"
        ) as cur:
            rows = await cur.fetchall()
            return [
                {"id": r[0], "email": r[1], "telegram_id": r[2], "name": r[3], "movies": r[4]}
                for r in rows
            ]


async def main() -> None:
    # Postgres pool требует явной инициализации, SQLite — нет.
    if os.environ.get("DATABASE_URL"):
        from backend import db_postgres
        await db_postgres.init_db()

    users = await list_users()
    print("\n=== Все юзеры ===")
    for u in users:
        tg = f"tg={u['telegram_id']}" if u["telegram_id"] else "tg=—"
        print(f"  id={u['id']:>3}  {tg:<14}  movies={u['movies']:>3}  email={u['email']:<35}  name={u['name']}")

    print()
    try:
        source = int(input("Source user id (откуда переносим фильмы): ").strip())
        target = int(input("Target user id (куда — обычно Telegram-аккаунт): ").strip())
    except (ValueError, EOFError):
        print("Отмена.")
        return

    if source == target:
        print("Source и target совпадают, нечего делать.")
        return

    src = next((u for u in users if u["id"] == source), None)
    tgt = next((u for u in users if u["id"] == target), None)
    if not src or not tgt:
        print("Один из id не найден в списке юзеров.")
        return

    print(f"\nПеренесу {src['movies']} фильмов с user {source} ({src['email']}) → "
          f"user {target} ({tgt['email']}, tg_id={tgt['telegram_id']}).")
    print(f"После переноса user {source} будет УДАЛЁН.")
    confirm = input("Подтвердить? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Отмена.")
        return

    await db.merge_telegram_user_into(source_user_id=source, target_user_id=target)
    print("✓ Готово.")

    fresh = await list_users()
    print("\n=== После миграции ===")
    for u in fresh:
        tg = f"tg={u['telegram_id']}" if u["telegram_id"] else "tg=—"
        print(f"  id={u['id']:>3}  {tg:<14}  movies={u['movies']:>3}  email={u['email']:<35}  name={u['name']}")


if __name__ == "__main__":
    asyncio.run(main())
