# PostgreSQL backend using asyncpg.
#
# HOW TO ACTIVATE ON RAILWAY:
# 1. In Railway Dashboard → your project → "+ New" → "Database" → "PostgreSQL"
# 2. Click the new PostgreSQL service → "Connect" tab → copy "DATABASE_URL"
# 3. Go to your movie_picker service → "Variables" → add:
#    DATABASE_URL = <paste the value from step 2>
# 4. Redeploy — the app will use PostgreSQL automatically.
#
# Local dev: just don't set DATABASE_URL and SQLite will be used as before.

import asyncpg
import json
import os
from datetime import datetime
from typing import Optional

from backend.models.movie import Movie, MovieBase
from backend.models.book import Book, BookBase

SELECT_COLUMNS = (
    "id, imdb_id, title, original_title, year, genres, description, plot, "
    '"cast", director, poster_url, imdb_rating, awards, is_watched, source, '
    "added_at, rec_source, rec_note, in_library, award, award_year, plot_ru, "
    "user_rating, user_note, watched_at, media_type, source_url"
)

BOOK_SELECT_COLUMNS = (
    "id, work_key, title, authors, year, subjects, description, cover_url, "
    "rating, is_read, source, rec_source, rec_note, in_library, added_at, "
    "user_rating, user_note, read_at"
)

_pool: Optional[asyncpg.Pool] = None


def _get_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    # Railway sometimes gives postgres:// — asyncpg needs postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


async def init_db() -> None:
    global _pool
    url = _get_url()
    _pool = await asyncpg.create_pool(url, min_size=1, max_size=5, ssl="require")
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                google_sub TEXT UNIQUE,
                telegram_id BIGINT UNIQUE,
                name TEXT,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Миграция для существующих БД без telegram_id (Railway уже задеплоен).
        # BIGINT — у телеграма user_id может быть > 2^31.
        await conn.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id BIGINT"
        )
        await conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id "
            "ON users(telegram_id) WHERE telegram_id IS NOT NULL"
        )
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub)"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                imdb_id TEXT NOT NULL,
                title TEXT NOT NULL,
                original_title TEXT,
                year INTEGER,
                genres TEXT DEFAULT '[]',
                description TEXT,
                plot TEXT,
                "cast" TEXT DEFAULT '[]',
                director TEXT,
                poster_url TEXT,
                imdb_rating REAL,
                awards TEXT,
                is_watched BOOLEAN DEFAULT FALSE,
                source TEXT DEFAULT 'personal',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rec_source TEXT,
                rec_note TEXT,
                in_library BOOLEAN DEFAULT TRUE,
                award TEXT,
                award_year INTEGER,
                plot_ru TEXT
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_imdb_id ON movies(imdb_id)"
        )
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON movies(source)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON movies(user_id)")
        await conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_imdb "
            "ON movies(user_id, imdb_id) WHERE user_id IS NOT NULL"
        )
        # Дневник для фильмов: личная оценка/заметка/дата просмотра.
        await conn.execute("ALTER TABLE movies ADD COLUMN IF NOT EXISTS user_rating REAL")
        await conn.execute("ALTER TABLE movies ADD COLUMN IF NOT EXISTS user_note TEXT")
        await conn.execute("ALTER TABLE movies ADD COLUMN IF NOT EXISTS watched_at TIMESTAMP")
        # movie / series — для разбивки библиотеки на «Фильмы» и «Сериалы».
        await conn.execute(
            "ALTER TABLE movies ADD COLUMN IF NOT EXISTS media_type TEXT DEFAULT 'movie'"
        )
        # Ссылка на оригинал рекомендации (Reel / пост в канале).
        await conn.execute(
            "ALTER TABLE movies ADD COLUMN IF NOT EXISTS source_url TEXT"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shared_lists (
                id SERIAL PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                name TEXT NOT NULL,
                snapshot TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                view_count INTEGER DEFAULT 0
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_shared_lists_slug ON shared_lists(slug)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_shared_lists_expires "
            "ON shared_lists(expires_at)"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                work_key TEXT NOT NULL,
                title TEXT NOT NULL,
                authors TEXT DEFAULT '[]',
                year INTEGER,
                subjects TEXT DEFAULT '[]',
                description TEXT,
                cover_url TEXT,
                rating REAL,
                is_read BOOLEAN DEFAULT FALSE,
                source TEXT DEFAULT 'personal',
                rec_source TEXT,
                rec_note TEXT,
                in_library BOOLEAN DEFAULT TRUE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_books_user_id ON books(user_id)")
        await conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_books_user_work "
            "ON books(user_id, work_key) WHERE user_id IS NOT NULL"
        )
        # Дневник для книг: личная оценка/заметка/дата прочтения.
        await conn.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS user_rating REAL")
        await conn.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS user_note TEXT")
        await conn.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS read_at TIMESTAMP")

        # Маркеры разовых миграций/бэкфиллов (key → value), чтобы они отрабатывали
        # на старте один раз и не гоняли OMDB/LLM при каждом деплое.
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Разовый бэкфилл: бот раньше писал source='telegram' всему подряд.
        # source — тип записи (personal/top100/awards), канал рекомендации живёт
        # в rec_source. Реальный источник старых строк неизвестен → personal.
        done = await conn.fetchval(
            "SELECT value FROM app_meta WHERE key = 'bot_source_backfill_v1'"
        )
        if not done:
            await conn.execute(
                "UPDATE movies SET source = 'personal' WHERE source = 'telegram'"
            )
            await conn.execute(
                "UPDATE books SET source = 'personal' WHERE source = 'telegram'"
            )
            await conn.execute(
                "INSERT INTO app_meta (key, value) "
                "VALUES ('bot_source_backfill_v1', 'done') "
                "ON CONFLICT (key) DO NOTHING"
            )


async def meta_get(key: str) -> Optional[str]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("SELECT value FROM app_meta WHERE key = $1", key)
        return row[0] if row else None


async def meta_set(key: str, value: str) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO app_meta (key, value) VALUES ($1, $2) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            key, value,
        )


async def get_all_movie_imdb_ids() -> list[str]:
    """Уникальные imdb_id по всем строкам movies (для разовых бэкфиллов)."""
    async with _pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT imdb_id FROM movies")
    return [r[0] for r in rows if r[0]]


async def set_media_type_by_imdb(imdb_id: str, media_type: str) -> int:
    """Проставляет media_type всем строкам с этим imdb_id (тип общий для тайтла,
    так покрываем сразу всех пользователей). Возвращает число изменённых строк."""
    async with _pool.acquire() as conn:
        res = await conn.execute(
            "UPDATE movies SET media_type = $1 "
            "WHERE imdb_id = $2 AND media_type IS DISTINCT FROM $1",
            media_type, imdb_id,
        )
    return int(res.split()[-1])


def _row_to_movie(row) -> Movie:
    return Movie(
        id=row[0],
        imdb_id=row[1],
        title=row[2],
        original_title=row[3],
        year=row[4],
        genres=json.loads(row[5]) if row[5] else [],
        description=row[6],
        plot=row[7],
        cast=json.loads(row[8]) if row[8] else [],
        director=row[9],
        poster_url=row[10],
        imdb_rating=row[11],
        awards=row[12],
        is_watched=bool(row[13]),
        source=row[14],
        added_at=row[15] if isinstance(row[15], datetime) else (
            datetime.fromisoformat(str(row[15])) if row[15] else datetime.now()
        ),
        rec_source=row[16],
        rec_note=row[17],
        in_library=bool(row[18]) if row[18] is not None else True,
        award=row[19],
        award_year=row[20],
        plot_ru=row[21],
        user_rating=row[22],
        user_note=row[23],
        watched_at=row[24] if (row[24] is None or isinstance(row[24], datetime)) else (
            datetime.fromisoformat(str(row[24])) if row[24] else None
        ),
        media_type=row[25] or "movie",
        source_url=row[26],
    )


_USER_COLS = (
    "id, email, password_hash, google_sub, telegram_id, name, avatar_url, created_at"
)


def _row_to_user(row) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "google_sub": row[3],
        "telegram_id": row[4],
        "name": row[5],
        "avatar_url": row[6],
        "created_at": row[7] if isinstance(row[7], datetime) else datetime.now(),
    }


# ── users ────────────────────────────────────────────────────────────────────


async def get_user_by_id(user_id: int) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {_USER_COLS} FROM users WHERE id = $1",
            user_id,
        )
        return _row_to_user(row) if row else None


async def get_user_by_email(email: str) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {_USER_COLS} FROM users WHERE email = $1",
            email.lower(),
        )
        return _row_to_user(row) if row else None


async def get_user_by_google_sub(google_sub: str) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {_USER_COLS} FROM users WHERE google_sub = $1",
            google_sub,
        )
        return _row_to_user(row) if row else None


async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {_USER_COLS} FROM users WHERE telegram_id = $1",
            telegram_id,
        )
        return _row_to_user(row) if row else None


async def create_user(
    email: str,
    password_hash: Optional[str] = None,
    google_sub: Optional[str] = None,
    telegram_id: Optional[int] = None,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> dict:
    async with _pool.acquire() as conn:
        user_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash, google_sub, telegram_id, name, avatar_url) "
            "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            email.lower(), password_hash, google_sub, telegram_id, name, avatar_url,
        )
    return await get_user_by_id(user_id)


async def merge_telegram_user_into(source_user_id: int, target_user_id: int) -> None:
    """См. docstring в db_sqlite.merge_telegram_user_into — поведение идентичное."""
    if source_user_id == target_user_id:
        return
    async with _pool.acquire() as conn:
        async with conn.transaction():
            source_tg_id = await conn.fetchval(
                "SELECT telegram_id FROM users WHERE id = $1", source_user_id
            )
            # Снимаем фильмы source'а, уже лежащие на полке у target (UNIQUE по imdb_id).
            await conn.execute(
                "DELETE FROM movies WHERE user_id = $1 AND imdb_id IN "
                "(SELECT imdb_id FROM movies WHERE user_id = $2)",
                source_user_id, target_user_id,
            )
            await conn.execute(
                "UPDATE movies SET user_id = $1 WHERE user_id = $2",
                target_user_id, source_user_id,
            )
            if source_tg_id is not None:
                await conn.execute(
                    "UPDATE users SET telegram_id = NULL WHERE id = $1",
                    source_user_id,
                )
                await conn.execute(
                    "UPDATE users SET telegram_id = $1 WHERE id = $2",
                    source_tg_id, target_user_id,
                )
            await conn.execute("DELETE FROM users WHERE id = $1", source_user_id)


async def attach_google_sub(
    user_id: int, google_sub: str, avatar_url: Optional[str]
) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET google_sub = $1, "
            "avatar_url = COALESCE(avatar_url, $2) WHERE id = $3",
            google_sub, avatar_url, user_id,
        )


# ── movies ───────────────────────────────────────────────────────────────────


async def get_all_movies(
    user_id: int,
    source: Optional[str] = None,
    is_watched: Optional[bool] = None,
    in_library: Optional[bool] = None,
) -> list[Movie]:
    conditions = ["user_id = $1"]
    params: list = [user_id]

    if source:
        params.append(source)
        conditions.append(f"source = ${len(params)}")
    if is_watched is not None:
        params.append(is_watched)
        conditions.append(f"is_watched = ${len(params)}")
    if in_library is not None:
        params.append(in_library)
        conditions.append(f"in_library = ${len(params)}")

    query = (
        f"SELECT {SELECT_COLUMNS} FROM movies "
        f"WHERE {' AND '.join(conditions)} "
        "ORDER BY added_at DESC"
    )
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [_row_to_movie(r) for r in rows]


async def get_awards(limit: Optional[int] = None) -> list[Movie]:
    query = (
        f"SELECT {SELECT_COLUMNS} FROM movies "
        "WHERE user_id IS NULL AND source = 'awards' "
        "ORDER BY COALESCE(award_year, year) DESC NULLS LAST, title ASC"
    )
    if limit:
        query += f" LIMIT {int(limit)}"
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query)
        return [_row_to_movie(r) for r in rows]


async def get_award_catalog_entry(movie_id: int) -> Optional[Movie]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE id = $1 AND user_id IS NULL",
            movie_id,
        )
        return _row_to_movie(row) if row else None


async def get_user_movie_by_id(movie_id: int, user_id: int) -> Optional[Movie]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {SELECT_COLUMNS} FROM movies WHERE id = $1 AND user_id = $2",
            movie_id, user_id,
        )
        return _row_to_movie(row) if row else None


async def get_user_movie_by_imdb_id(imdb_id: str, user_id: int) -> Optional[Movie]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE imdb_id = $1 AND user_id = $2",
            imdb_id, user_id,
        )
        return _row_to_movie(row) if row else None


async def get_award_by_imdb_id(imdb_id: str) -> Optional[Movie]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE imdb_id = $1 AND user_id IS NULL AND source = 'awards'",
            imdb_id,
        )
        return _row_to_movie(row) if row else None


async def add_movie(
    movie: MovieBase,
    user_id: Optional[int],
    source: str = "personal",
    rec_source: Optional[str] = None,
    rec_note: Optional[str] = None,
    in_library: bool = True,
    award: Optional[str] = None,
    award_year: Optional[int] = None,
    source_url: Optional[str] = None,
) -> Movie:
    async with _pool.acquire() as conn:
        movie_id = await conn.fetchval(
            """
            INSERT INTO movies (
                user_id, imdb_id, title, original_title, year, genres, description,
                plot, "cast", director, poster_url, imdb_rating, awards, source,
                rec_source, rec_note, in_library, award, award_year, media_type,
                source_url
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
            ) RETURNING id
            """,
            user_id,
            movie.imdb_id,
            movie.title,
            movie.original_title,
            movie.year,
            json.dumps(movie.genres),
            movie.description,
            movie.plot,
            json.dumps(movie.cast),
            movie.director,
            movie.poster_url,
            movie.imdb_rating,
            movie.awards,
            source,
            rec_source,
            rec_note,
            in_library,
            award,
            award_year,
            movie.media_type,
            source_url,
        )
        row = await conn.fetchrow(
            f"SELECT {SELECT_COLUMNS} FROM movies WHERE id = $1", movie_id
        )
        return _row_to_movie(row)


async def update_movie(
    movie_id: int,
    user_id: int,
    is_watched: Optional[bool] = None,
    rec_source: Optional[str] = None,
    rec_note: Optional[str] = None,
    in_library: Optional[bool] = None,
    user_rating: Optional[float] = None,
    user_note: Optional[str] = None,
) -> Optional[Movie]:
    sets = []
    params: list = []

    if is_watched is not None:
        params.append(is_watched)
        sets.append(f"is_watched = ${len(params)}")
        if is_watched:
            params.append(datetime.now())
            sets.append(f"watched_at = COALESCE(watched_at, ${len(params)})")
    if rec_source is not None:
        params.append(rec_source)
        sets.append(f"rec_source = ${len(params)}")
    if rec_note is not None:
        params.append(rec_note)
        sets.append(f"rec_note = ${len(params)}")
    if in_library is not None:
        params.append(in_library)
        sets.append(f"in_library = ${len(params)}")
    if user_rating is not None:
        params.append(user_rating if user_rating > 0 else None)
        sets.append(f"user_rating = ${len(params)}")
    if user_note is not None:
        params.append(user_note or None)
        sets.append(f"user_note = ${len(params)}")

    if not sets:
        return await get_user_movie_by_id(movie_id, user_id)

    params.append(movie_id)
    n_id = len(params)
    params.append(user_id)
    n_uid = len(params)

    async with _pool.acquire() as conn:
        await conn.execute(
            f"UPDATE movies SET {', '.join(sets)} "
            f"WHERE id = ${n_id} AND user_id = ${n_uid}",
            *params,
        )
    return await get_user_movie_by_id(movie_id, user_id)


async def set_plot_ru(movie_id: int, plot_ru: str) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE movies SET plot_ru = $1 WHERE id = $2", plot_ru, movie_id
        )


async def set_description(movie_id: int, description: str) -> None:
    """Сохранить краткое описание. Догенерация в фоне после сохранения в боте."""
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE movies SET description = $1 WHERE id = $2", description, movie_id
        )


async def get_movies_missing_plot_ru() -> list[Movie]:
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE plot IS NOT NULL AND plot != '' AND plot != 'N/A' "
            "AND (plot_ru IS NULL OR plot_ru = '')"
        )
        return [_row_to_movie(r) for r in rows]


async def delete_movie(movie_id: int, user_id: int) -> bool:
    async with _pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM movies WHERE id = $1 AND user_id = $2",
            movie_id, user_id,
        )
        try:
            return int(result.split()[-1]) > 0
        except Exception:
            return False


async def get_unwatched_movies(user_id: int) -> list[Movie]:
    return await get_all_movies(user_id=user_id, is_watched=False, in_library=True)


# ── books ────────────────────────────────────────────────────────────────────


def _row_to_book(row) -> Book:
    return Book(
        id=row[0],
        work_key=row[1],
        title=row[2],
        authors=json.loads(row[3]) if row[3] else [],
        year=row[4],
        subjects=json.loads(row[5]) if row[5] else [],
        description=row[6],
        cover_url=row[7],
        rating=row[8],
        is_read=bool(row[9]),
        source=row[10],
        rec_source=row[11],
        rec_note=row[12],
        in_library=bool(row[13]) if row[13] is not None else True,
        added_at=row[14] if isinstance(row[14], datetime) else (
            datetime.fromisoformat(str(row[14])) if row[14] else datetime.now()
        ),
        user_rating=row[15],
        user_note=row[16],
        read_at=row[17] if (row[17] is None or isinstance(row[17], datetime)) else (
            datetime.fromisoformat(str(row[17])) if row[17] else None
        ),
    )


async def get_all_books(
    user_id: int,
    source: Optional[str] = None,
    is_read: Optional[bool] = None,
    in_library: Optional[bool] = None,
) -> list[Book]:
    conditions = ["user_id = $1"]
    params: list = [user_id]
    if source:
        params.append(source)
        conditions.append(f"source = ${len(params)}")
    if is_read is not None:
        params.append(is_read)
        conditions.append(f"is_read = ${len(params)}")
    if in_library is not None:
        params.append(in_library)
        conditions.append(f"in_library = ${len(params)}")
    query = (
        f"SELECT {BOOK_SELECT_COLUMNS} FROM books "
        f"WHERE {' AND '.join(conditions)} "
        "ORDER BY added_at DESC"
    )
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [_row_to_book(r) for r in rows]


async def get_unread_books(user_id: int) -> list[Book]:
    return await get_all_books(user_id=user_id, is_read=False, in_library=True)


async def get_user_book_by_id(book_id: int, user_id: int) -> Optional[Book]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {BOOK_SELECT_COLUMNS} FROM books WHERE id = $1 AND user_id = $2",
            book_id, user_id,
        )
        return _row_to_book(row) if row else None


async def get_user_book_by_work_key(work_key: str, user_id: int) -> Optional[Book]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {BOOK_SELECT_COLUMNS} FROM books WHERE work_key = $1 AND user_id = $2",
            work_key, user_id,
        )
        return _row_to_book(row) if row else None


async def add_book(
    book: BookBase,
    user_id: int,
    source: str = "personal",
    rec_source: Optional[str] = None,
    rec_note: Optional[str] = None,
    in_library: bool = True,
) -> Book:
    async with _pool.acquire() as conn:
        book_id = await conn.fetchval(
            """
            INSERT INTO books (
                user_id, work_key, title, authors, year, subjects, description,
                cover_url, rating, source, rec_source, rec_note, in_library
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
            ) RETURNING id
            """,
            user_id,
            book.work_key,
            book.title,
            json.dumps(book.authors),
            book.year,
            json.dumps(book.subjects),
            book.description,
            book.cover_url,
            book.rating,
            source,
            rec_source,
            rec_note,
            in_library,
        )
        row = await conn.fetchrow(
            f"SELECT {BOOK_SELECT_COLUMNS} FROM books WHERE id = $1", book_id
        )
        return _row_to_book(row)


async def update_book(
    book_id: int,
    user_id: int,
    is_read: Optional[bool] = None,
    rec_source: Optional[str] = None,
    rec_note: Optional[str] = None,
    in_library: Optional[bool] = None,
    user_rating: Optional[float] = None,
    user_note: Optional[str] = None,
) -> Optional[Book]:
    sets = []
    params: list = []
    if is_read is not None:
        params.append(is_read)
        sets.append(f"is_read = ${len(params)}")
        if is_read:
            params.append(datetime.now())
            sets.append(f"read_at = COALESCE(read_at, ${len(params)})")
    if rec_source is not None:
        params.append(rec_source)
        sets.append(f"rec_source = ${len(params)}")
    if rec_note is not None:
        params.append(rec_note)
        sets.append(f"rec_note = ${len(params)}")
    if in_library is not None:
        params.append(in_library)
        sets.append(f"in_library = ${len(params)}")
    if user_rating is not None:
        params.append(user_rating if user_rating > 0 else None)
        sets.append(f"user_rating = ${len(params)}")
    if user_note is not None:
        params.append(user_note or None)
        sets.append(f"user_note = ${len(params)}")
    if not sets:
        return await get_user_book_by_id(book_id, user_id)

    params.append(book_id)
    n_id = len(params)
    params.append(user_id)
    n_uid = len(params)
    async with _pool.acquire() as conn:
        await conn.execute(
            f"UPDATE books SET {', '.join(sets)} "
            f"WHERE id = ${n_id} AND user_id = ${n_uid}",
            *params,
        )
    return await get_user_book_by_id(book_id, user_id)


async def delete_book(book_id: int, user_id: int) -> bool:
    async with _pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM books WHERE id = $1 AND user_id = $2",
            book_id, user_id,
        )
        try:
            return int(result.split()[-1]) > 0
        except Exception:
            return False


# ── shared lists ─────────────────────────────────────────────────────────────


async def slug_exists(slug: str) -> bool:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM shared_lists WHERE slug = $1", slug,
        )
        return row is not None


async def create_share(
    slug: str,
    owner_user_id: Optional[int],
    name: str,
    snapshot_json: str,
    expires_at: Optional[datetime],
) -> dict:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO shared_lists (slug, owner_user_id, name, snapshot, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, slug, owner_user_id, name, snapshot, created_at,
                      expires_at, view_count
            """,
            slug, owner_user_id, name, snapshot_json, expires_at,
        )
        return _row_to_share(row)


async def get_share_by_slug(slug: str) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, slug, owner_user_id, name, snapshot, created_at, "
            "expires_at, view_count FROM shared_lists WHERE slug = $1",
            slug,
        )
        if not row:
            return None
        share = _row_to_share(row)

        if share["expires_at"] and share["expires_at"] < datetime.utcnow():
            return None

        try:
            await conn.execute(
                "UPDATE shared_lists SET view_count = view_count + 1 WHERE slug = $1",
                slug,
            )
        except Exception:
            pass

        return share


def _row_to_share(row) -> dict:
    return {
        "id": row[0],
        "slug": row[1],
        "owner_user_id": row[2],
        "name": row[3],
        "snapshot": row[4],
        "created_at": row[5] if isinstance(row[5], datetime) else (
            datetime.fromisoformat(str(row[5])) if row[5] else datetime.now()
        ),
        "expires_at": row[6] if (row[6] is None or isinstance(row[6], datetime)) else (
            datetime.fromisoformat(str(row[6])) if row[6] else None
        ),
        "view_count": row[7] or 0,
    }
