import aiosqlite
import json
from datetime import datetime
from typing import Optional
from backend.config import DATABASE_PATH
from backend.models.movie import Movie, MovieBase


SELECT_COLUMNS = (
    "id, imdb_id, title, original_title, year, genres, description, plot, "
    '"cast", director, poster_url, imdb_rating, awards, is_watched, source, '
    "added_at, rec_source, rec_note, in_library, award, award_year, plot_ru"
)


async def _column_exists(db: aiosqlite.Connection, table: str, column: str) -> bool:
    async with db.execute(f"PRAGMA table_info({table})") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    return column in cols


async def _ensure_column(db: aiosqlite.Connection, column: str, decl: str) -> None:
    if not await _column_exists(db, "movies", column):
        await db.execute(f"ALTER TABLE movies ADD COLUMN {column} {decl}")


async def _ensure_users_table(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            google_sub TEXT UNIQUE,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Миграция для уже существующих БД, где telegram_id ещё нет.
    async with db.execute("PRAGMA table_info(users)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    if "telegram_id" not in cols:
        await db.execute("ALTER TABLE users ADD COLUMN telegram_id INTEGER")
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id "
            "ON users(telegram_id) WHERE telegram_id IS NOT NULL"
        )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub)")
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id) "
        "WHERE telegram_id IS NOT NULL"
    )


async def _migrate_movies_add_user_id(db: aiosqlite.Connection) -> None:
    """Добавляет user_id в movies и снимает UNIQUE с imdb_id.

    В старой схеме `imdb_id UNIQUE` не позволял держать один фильм у разных юзеров.
    После миграции уникальность обеспечивается на уровне приложения в связке
    (user_id, imdb_id).
    """
    if await _column_exists(db, "movies", "user_id"):
        return

    await db.execute("ALTER TABLE movies RENAME TO movies_old")
    await db.execute("""
        CREATE TABLE movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            imdb_id TEXT NOT NULL,
            title TEXT NOT NULL,
            original_title TEXT,
            year INTEGER,
            genres TEXT DEFAULT '[]',
            description TEXT,
            plot TEXT,
            cast TEXT DEFAULT '[]',
            director TEXT,
            poster_url TEXT,
            imdb_rating REAL,
            awards TEXT,
            is_watched BOOLEAN DEFAULT FALSE,
            source TEXT DEFAULT 'personal',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rec_source TEXT,
            rec_note TEXT,
            in_library BOOLEAN DEFAULT 1,
            award TEXT,
            award_year INTEGER,
            plot_ru TEXT
        )
    """)
    await db.execute("""
        INSERT INTO movies (
            id, user_id, imdb_id, title, original_title, year, genres, description, plot,
            cast, director, poster_url, imdb_rating, awards, is_watched, source, added_at,
            rec_source, rec_note, in_library, award, award_year, plot_ru
        )
        SELECT
            id, NULL, imdb_id, title, original_title, year, genres, description, plot,
            "cast", director, poster_url, imdb_rating, awards, is_watched, source, added_at,
            rec_source, rec_note, in_library, award, award_year, plot_ru
        FROM movies_old
    """)
    await db.execute("DROP TABLE movies_old")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_imdb_id ON movies(imdb_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_source ON movies(source)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON movies(user_id)")
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_imdb ON movies(user_id, imdb_id)"
    )


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # WAL: читатели не блокируют писателей.
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await _ensure_users_table(db)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imdb_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                original_title TEXT,
                year INTEGER,
                genres TEXT DEFAULT '[]',
                description TEXT,
                plot TEXT,
                cast TEXT DEFAULT '[]',
                director TEXT,
                poster_url TEXT,
                imdb_rating REAL,
                awards TEXT,
                is_watched BOOLEAN DEFAULT FALSE,
                source TEXT DEFAULT 'personal',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await _ensure_column(db, "rec_source", "TEXT")
        await _ensure_column(db, "rec_note", "TEXT")
        await _ensure_column(db, "in_library", "BOOLEAN DEFAULT 1")
        await _ensure_column(db, "award", "TEXT")
        await _ensure_column(db, "award_year", "INTEGER")
        await _ensure_column(db, "plot_ru", "TEXT")

        await _migrate_movies_add_user_id(db)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_imdb_id ON movies(imdb_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_source ON movies(source)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON movies(user_id)")
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_imdb ON movies(user_id, imdb_id)"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shared_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                name TEXT NOT NULL,
                snapshot TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                view_count INTEGER DEFAULT 0
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_shared_lists_slug ON shared_lists(slug)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_shared_lists_expires "
            "ON shared_lists(expires_at)"
        )
        await db.commit()


# ----- users ---------------------------------------------------------------


async def claim_orphan_library_for_user(user_id: int) -> int:
    """Привязать к пользователю все «бесхозные» записи личной библиотеки.

    Нужно для миграции: исторически было 62 фильма без владельца. Первый
    зарегистрировавшийся пользователь забирает их себе. Срабатывает
    максимум один раз — потом бесхозных записей просто нет.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE movies SET user_id = ? "
            "WHERE user_id IS NULL AND in_library = 1",
            (user_id,),
        )
        await db.commit()
        return cursor.rowcount or 0


async def has_any_users() -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT 1 FROM users LIMIT 1") as cur:
            return (await cur.fetchone()) is not None


_USER_COLS = (
    "id, email, password_hash, google_sub, telegram_id, name, avatar_url, created_at"
)


async def get_user_by_id(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT {_USER_COLS} FROM users WHERE id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_user(row) if row else None


async def get_user_by_email(email: str) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT {_USER_COLS} FROM users WHERE email = ?",
            (email.lower(),),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_user(row) if row else None


async def get_user_by_google_sub(google_sub: str) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT {_USER_COLS} FROM users WHERE google_sub = ?",
            (google_sub,),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_user(row) if row else None


async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT {_USER_COLS} FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_user(row) if row else None


async def create_user(
    email: str,
    password_hash: Optional[str] = None,
    google_sub: Optional[str] = None,
    telegram_id: Optional[int] = None,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO users (email, password_hash, google_sub, telegram_id, name, avatar_url) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (email.lower(), password_hash, google_sub, telegram_id, name, avatar_url),
        )
        await db.commit()
        user_id = cursor.lastrowid
    return await get_user_by_id(user_id)


async def attach_google_sub(user_id: int, google_sub: str, avatar_url: Optional[str]) -> None:
    """Привязать Google-аккаунт к уже существующему email-аккаунту."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET google_sub = ?, "
            "avatar_url = COALESCE(avatar_url, ?) WHERE id = ?",
            (google_sub, avatar_url, user_id),
        )
        await db.commit()


def _row_to_user(row) -> dict:
    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "google_sub": row[3],
        "telegram_id": row[4],
        "name": row[5],
        "avatar_url": row[6],
        "created_at": datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
    }


# ----- movies --------------------------------------------------------------


def _row_to_movie(row: aiosqlite.Row) -> Movie:
    """Преобразование строки БД в модель Movie"""
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
        added_at=datetime.fromisoformat(row[15]) if row[15] else datetime.now(),
        rec_source=row[16],
        rec_note=row[17],
        in_library=bool(row[18]) if row[18] is not None else True,
        award=row[19],
        award_year=row[20],
        plot_ru=row[21],
    )


async def get_all_movies(
    user_id: int,
    source: Optional[str] = None,
    is_watched: Optional[bool] = None,
    in_library: Optional[bool] = None,
) -> list[Movie]:
    """Фильмы пользователя с опциональной фильтрацией."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = f"SELECT {SELECT_COLUMNS} FROM movies WHERE user_id = ?"
        params: list = [user_id]

        if source:
            query += " AND source = ?"
            params.append(source)
        if is_watched is not None:
            query += " AND is_watched = ?"
            params.append(is_watched)
        if in_library is not None:
            query += " AND in_library = ?"
            params.append(1 if in_library else 0)

        query += " ORDER BY added_at DESC"

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_movie(row) for row in rows]


async def get_awards(limit: Optional[int] = None) -> list[Movie]:
    """Каталог лауреатов (глобальный, user_id IS NULL)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = (
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE user_id IS NULL AND source = 'awards' "
            "ORDER BY COALESCE(award_year, year) DESC, title ASC"
        )
        if limit:
            query += f" LIMIT {int(limit)}"
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_movie(row) for row in rows]


async def get_award_catalog_entry(movie_id: int) -> Optional[Movie]:
    """Запись из глобального каталога наград (без user_id)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE id = ? AND user_id IS NULL",
            (movie_id,),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_movie(row) if row else None


async def get_user_movie_by_id(movie_id: int, user_id: int) -> Optional[Movie]:
    """Фильм из библиотеки конкретного юзера по PK."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT {SELECT_COLUMNS} FROM movies WHERE id = ? AND user_id = ?",
            (movie_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return _row_to_movie(row) if row else None


async def get_user_movie_by_imdb_id(imdb_id: str, user_id: int) -> Optional[Movie]:
    """Фильм из библиотеки конкретного юзера по IMDb ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT {SELECT_COLUMNS} FROM movies WHERE imdb_id = ? AND user_id = ?",
            (imdb_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return _row_to_movie(row) if row else None


async def get_award_by_imdb_id(imdb_id: str) -> Optional[Movie]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE imdb_id = ? AND user_id IS NULL AND source = 'awards'",
            (imdb_id,),
        ) as cur:
            row = await cur.fetchone()
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
) -> Movie:
    """Добавить фильм. `user_id=None` — глобальная запись (каталог наград)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO movies (
                user_id, imdb_id, title, original_title, year, genres, description,
                plot, cast, director, poster_url, imdb_rating, awards, source,
                rec_source, rec_note, in_library, award, award_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
            1 if in_library else 0,
            award,
            award_year,
        ))
        await db.commit()
        movie_id = cursor.lastrowid
        async with db.execute(
            f"SELECT {SELECT_COLUMNS} FROM movies WHERE id = ?", (movie_id,)
        ) as cur:
            row = await cur.fetchone()
            return _row_to_movie(row)


async def update_movie(
    movie_id: int,
    user_id: int,
    is_watched: Optional[bool] = None,
    rec_source: Optional[str] = None,
    rec_note: Optional[str] = None,
    in_library: Optional[bool] = None,
) -> Optional[Movie]:
    """Обновить поля фильма пользователя."""
    sets = []
    params: list = []
    if is_watched is not None:
        sets.append("is_watched = ?")
        params.append(1 if is_watched else 0)
    if rec_source is not None:
        sets.append("rec_source = ?")
        params.append(rec_source)
    if rec_note is not None:
        sets.append("rec_note = ?")
        params.append(rec_note)
    if in_library is not None:
        sets.append("in_library = ?")
        params.append(1 if in_library else 0)
    if not sets:
        return await get_user_movie_by_id(movie_id, user_id)

    params.extend([movie_id, user_id])
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            f"UPDATE movies SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
            params,
        )
        await db.commit()
        return await get_user_movie_by_id(movie_id, user_id)


async def set_plot_ru(movie_id: int, plot_ru: str) -> None:
    """Сохранить перевод сюжета. Используется фоновым переводчиком по PK."""
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        await conn.execute("UPDATE movies SET plot_ru = ? WHERE id = ?", (plot_ru, movie_id))
        await conn.commit()


async def get_movies_missing_plot_ru() -> list[Movie]:
    """Любые фильмы (каталог или личные) без русского перевода сюжета."""
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        query = (
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE plot IS NOT NULL AND plot != '' AND plot != 'N/A' "
            "AND (plot_ru IS NULL OR plot_ru = '')"
        )
        async with conn.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_movie(row) for row in rows]


async def delete_movie(movie_id: int, user_id: int) -> bool:
    """Удалить фильм из библиотеки пользователя."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM movies WHERE id = ? AND user_id = ?",
            (movie_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_unwatched_movies(user_id: int) -> list[Movie]:
    """Непросмотренные фильмы пользователя для рекомендаций."""
    return await get_all_movies(user_id=user_id, is_watched=False, in_library=True)


# ----- shared lists --------------------------------------------------------


async def slug_exists(slug: str) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM shared_lists WHERE slug = ?", (slug,),
        ) as cur:
            return (await cur.fetchone()) is not None


async def create_share(
    slug: str,
    owner_user_id: Optional[int],
    name: str,
    snapshot_json: str,
    expires_at: Optional[datetime],
) -> dict:
    """Persist a snapshot of a movie list under ``slug``.

    Returns the row as a dict so the router can build SharedListResponse.
    The snapshot is opaque JSON — callers serialise on the way in and
    deserialise on the way out.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO shared_lists (slug, owner_user_id, name, snapshot, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                slug,
                owner_user_id,
                name,
                snapshot_json,
                expires_at.isoformat() if expires_at else None,
            ),
        )
        await db.commit()
        share_id = cursor.lastrowid
        async with db.execute(
            "SELECT id, slug, owner_user_id, name, snapshot, created_at, "
            "expires_at, view_count FROM shared_lists WHERE id = ?",
            (share_id,),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_share(row)


async def get_share_by_slug(slug: str) -> Optional[dict]:
    """Read a share. Returns None if missing or expired.

    Increments view_count opportunistically — failures aren't fatal because
    we don't want a write hiccup to break the read path.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT id, slug, owner_user_id, name, snapshot, created_at, "
            "expires_at, view_count FROM shared_lists WHERE slug = ?",
            (slug,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            share = _row_to_share(row)

        if share["expires_at"] and share["expires_at"] < datetime.utcnow():
            return None

        try:
            await db.execute(
                "UPDATE shared_lists SET view_count = view_count + 1 WHERE slug = ?",
                (slug,),
            )
            await db.commit()
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
        "created_at": (
            datetime.fromisoformat(row[5]) if row[5] else datetime.now()
        ),
        "expires_at": (
            datetime.fromisoformat(row[6]) if row[6] else None
        ),
        "view_count": row[7] or 0,
    }
