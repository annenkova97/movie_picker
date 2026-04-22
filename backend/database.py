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


async def _ensure_column(db: aiosqlite.Connection, column: str, decl: str) -> None:
    async with db.execute("PRAGMA table_info(movies)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    if column not in cols:
        await db.execute(f"ALTER TABLE movies ADD COLUMN {column} {decl}")


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # WAL: читатели не блокируют писателей — выдерживает несколько десятков
        # одновременных юзеров без "database is locked".
        await db.execute("PRAGMA journal_mode=WAL")
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
        # in_library: существующие записи — на полке пользователя (default 1),
        # новые записи каталога наград будут явно вставляться с 0
        await _ensure_column(db, "in_library", "BOOLEAN DEFAULT 1")
        await _ensure_column(db, "award", "TEXT")
        await _ensure_column(db, "award_year", "INTEGER")
        await _ensure_column(db, "plot_ru", "TEXT")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_imdb_id ON movies(imdb_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_source ON movies(source)")
        await db.commit()


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
    source: Optional[str] = None,
    is_watched: Optional[bool] = None,
    in_library: Optional[bool] = None,
) -> list[Movie]:
    """Получить все фильмы с опциональной фильтрацией"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = f"SELECT {SELECT_COLUMNS} FROM movies WHERE 1=1"
        params: list = []

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
    """Каталог лауреатов наград, сортировка по году награды (новые сверху)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = (
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE source = 'awards' "
            "ORDER BY COALESCE(award_year, year) DESC, title ASC"
        )
        if limit:
            query += f" LIMIT {int(limit)}"
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_movie(row) for row in rows]


async def get_movie_by_id(movie_id: int) -> Optional[Movie]:
    """Получить фильм по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(f"SELECT {SELECT_COLUMNS} FROM movies WHERE id = ?", (movie_id,)) as cursor:
            row = await cursor.fetchone()
            return _row_to_movie(row) if row else None


async def get_movie_by_imdb_id(imdb_id: str) -> Optional[Movie]:
    """Получить фильм по IMDb ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(f"SELECT {SELECT_COLUMNS} FROM movies WHERE imdb_id = ?", (imdb_id,)) as cursor:
            row = await cursor.fetchone()
            return _row_to_movie(row) if row else None


async def add_movie(
    movie: MovieBase,
    source: str = "personal",
    rec_source: Optional[str] = None,
    rec_note: Optional[str] = None,
    in_library: bool = True,
    award: Optional[str] = None,
    award_year: Optional[int] = None,
) -> Movie:
    """Добавить фильм в базу"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO movies (
                imdb_id, title, original_title, year, genres, description,
                plot, cast, director, poster_url, imdb_rating, awards, source,
                rec_source, rec_note, in_library, award, award_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
        return await get_movie_by_id(movie_id)


async def update_movie(
    movie_id: int,
    is_watched: Optional[bool] = None,
    rec_source: Optional[str] = None,
    rec_note: Optional[str] = None,
    in_library: Optional[bool] = None,
) -> Optional[Movie]:
    """Обновить поля фильма"""
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
        return await get_movie_by_id(movie_id)

    params.append(movie_id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"UPDATE movies SET {', '.join(sets)} WHERE id = ?", params)
        await db.commit()
        return await get_movie_by_id(movie_id)


async def set_plot_ru(movie_id: int, plot_ru: str) -> None:
    """Сохранить перевод сюжета на русский."""
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        await conn.execute("UPDATE movies SET plot_ru = ? WHERE id = ?", (plot_ru, movie_id))
        await conn.commit()


async def get_movies_missing_plot_ru() -> list[Movie]:
    """Фильмы, у которых есть plot на английском, но нет перевода."""
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        query = (
            f"SELECT {SELECT_COLUMNS} FROM movies "
            "WHERE plot IS NOT NULL AND plot != '' AND plot != 'N/A' "
            "AND (plot_ru IS NULL OR plot_ru = '')"
        )
        async with conn.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_movie(row) for row in rows]


async def delete_movie(movie_id: int) -> bool:
    """Удалить фильм из базы"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_unwatched_movies() -> list[Movie]:
    """Получить все непросмотренные фильмы пользователя для рекомендаций"""
    return await get_all_movies(is_watched=False, in_library=True)
