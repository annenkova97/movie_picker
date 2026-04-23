import asyncpg
import json
from datetime import datetime
from typing import Optional
from backend.config import DATABASE_URL
from backend.models.movie import Movie, MovieBase

_pool: asyncpg.Pool | None = None

SELECT_COLUMNS = (
    "id, imdb_id, title, original_title, year, genres, description, plot, "
    '"cast", director, poster_url, imdb_rating, awards, is_watched, source, '
    "added_at, rec_source, rec_note, in_library, award, award_year, plot_ru"
)


async def _column_exists(conn, table: str, column: str) -> bool:
    row = await conn.fetchrow(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = $1 AND column_name = $2",
        table, column,
    )
    return row is not None


async def _ensure_column(conn, column: str, decl: str) -> None:
    await conn.execute(f"ALTER TABLE movies ADD COLUMN IF NOT EXISTS {column} {decl}")


async def init_db():
    global _pool
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    _pool = await asyncpg.create_pool(url, ssl="require")

    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                google_sub TEXT UNIQUE,
                name TEXT,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_imdb_id ON movies(imdb_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON movies(source)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON movies(user_id)")
        await conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_imdb ON movies(user_id, imdb_id) "
            "WHERE user_id IS NOT NULL"
        )


# ----- users ---------------------------------------------------------------


async def claim_orphan_library_for_user(user_id: int) -> int:
    async with _pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE movies SET user_id = $1 WHERE user_id IS NULL AND in_library = TRUE",
            user_id,
        )
        return int(result.split()[-1])


async def has_any_users() -> bool:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM users LIMIT 1")
        return row is not None


async def get_user_by_id(user_id: int) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, google_sub, name, avatar_url, created_at "
            "FROM users WHERE id = $1",
            user_id,
        )
        return _row_to_user(row) if row else None


async def get_user_by_email(email: str) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, google_sub, name, avatar_url, created_at "
            "FROM users WHERE email = $1",
            email.lower(),
        )
        return _row_to_user(row) if row else None


async def get_user_by_google_sub(google_sub: str) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, google_sub, name, avatar_url, created_at "
            "FROM users WHERE google_sub = $1",
            google_sub,
        )
        return _row_to_user(row) if row else None


async def create_user(
    email: str,
    password_hash: Optional[str] = None,
    google_sub: Optional[str] = None,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> dict:
    async with _pool.acquire() as conn:
        user_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash, google_sub, name, avatar_url) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING id",
            email.lower(), password_hash, google_sub, name, avatar_url,
        )
    return await get_user_by_id(user_id)


async def attach_google_sub(user_id: int, google_sub: str, avatar_url: Optional[str]) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET google_sub = $1, "
            "avatar_url = COALESCE(avatar_url, $2) WHERE id = $3",
            google_sub, avatar_url, user_id,
        )


def _row_to_user(row) -> dict:
    created = row[6]
    if created is None:
        created = datetime.now()
    elif isinstance(created, str):
        created = datetime.fromisoformat(created)
    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "google_sub": row[3],
        "name": row[4],
        "avatar_url": row[5],
        "created_at": created,
    }


# ----- movies --------------------------------------------------------------


def _row_to_movie(row) -> Movie:
    added = row[15]
    if added is None:
        added = datetime.now()
    elif isinstance(added, str):
        added = datetime.fromisoformat(added)
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
        added_at=added,
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
    async with _pool.acquire() as conn:
        counter = 1
        query = f"SELECT {SELECT_COLUMNS} FROM movies WHERE user_id = ${counter}"
        params: list = [user_id]
        counter += 1

        if source:
            query += f" AND source = ${counter}"
            params.append(source)
            counter += 1
        if is_watched is not None:
            query += f" AND is_watched = ${counter}"
            params.append(is_watched)
            counter += 1
        if in_library is not None:
            query += f" AND in_library = ${counter}"
            params.append(in_library)
            counter += 1

        query += " ORDER BY added_at DESC"
        rows = await conn.fetch(query, *params)
        return [_row_to_movie(row) for row in rows]


async def get_awards(limit: Optional[int] = None) -> list[Movie]:
    async with _pool.acquire() as conn:
        query = (
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE user_id IS NULL AND source = 'awards' "
            "ORDER BY COALESCE(award_year, year) DESC, title ASC"
        )
        if limit:
            query += f" LIMIT {int(limit)}"
        rows = await conn.fetch(query)
        return [_row_to_movie(row) for row in rows]


async def get_award_catalog_entry(movie_id: int) -> Optional[Movie]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {SELECT_COLUMNS} FROM movies WHERE id = $1 AND user_id IS NULL",
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
            f"SELECT {SELECT_COLUMNS} FROM movies WHERE imdb_id = $1 AND user_id = $2",
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
) -> Movie:
    async with _pool.acquire() as conn:
        movie_id = await conn.fetchval(
            'INSERT INTO movies ('
            '    user_id, imdb_id, title, original_title, year, genres, description,'
            '    plot, "cast", director, poster_url, imdb_rating, awards, source,'
            '    rec_source, rec_note, in_library, award, award_year'
            ') VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)'
            ' RETURNING id',
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
) -> Optional[Movie]:
    sets = []
    params: list = []
    counter = 1
    if is_watched is not None:
        sets.append(f"is_watched = ${counter}")
        params.append(is_watched)
        counter += 1
    if rec_source is not None:
        sets.append(f"rec_source = ${counter}")
        params.append(rec_source)
        counter += 1
    if rec_note is not None:
        sets.append(f"rec_note = ${counter}")
        params.append(rec_note)
        counter += 1
    if in_library is not None:
        sets.append(f"in_library = ${counter}")
        params.append(in_library)
        counter += 1
    if not sets:
        return await get_user_movie_by_id(movie_id, user_id)

    params.extend([movie_id, user_id])
    async with _pool.acquire() as conn:
        await conn.execute(
            f"UPDATE movies SET {', '.join(sets)} "
            f"WHERE id = ${counter} AND user_id = ${counter + 1}",
            *params,
        )
    return await get_user_movie_by_id(movie_id, user_id)


async def set_plot_ru(movie_id: int, plot_ru: str) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE movies SET plot_ru = $1 WHERE id = $2", plot_ru, movie_id
        )


async def get_movies_missing_plot_ru() -> list[Movie]:
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE plot IS NOT NULL AND plot != '' AND plot != 'N/A' "
            "AND (plot_ru IS NULL OR plot_ru = '')"
        )
        return [_row_to_movie(row) for row in rows]


async def delete_movie(movie_id: int, user_id: int) -> bool:
    async with _pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM movies WHERE id = $1 AND user_id = $2",
            movie_id, user_id,
        )
        return int(result.split()[-1]) > 0


async def get_unwatched_movies(user_id: int) -> list[Movie]:
    return await get_all_movies(user_id=user_id, is_watched=False, in_library=True)
