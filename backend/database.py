import aiosqlite
import json
from datetime import datetime
from typing import Optional
from backend.config import DATABASE_PATH
from backend.models.movie import Movie, MovieBase


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
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
        added_at=datetime.fromisoformat(row[15]) if row[15] else datetime.now()
    )


async def get_all_movies(source: Optional[str] = None, is_watched: Optional[bool] = None) -> list[Movie]:
    """Получить все фильмы с опциональной фильтрацией"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = "SELECT * FROM movies WHERE 1=1"
        params = []

        if source:
            query += " AND source = ?"
            params.append(source)
        if is_watched is not None:
            query += " AND is_watched = ?"
            params.append(is_watched)

        query += " ORDER BY added_at DESC"

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_movie(row) for row in rows]


async def get_movie_by_id(movie_id: int) -> Optional[Movie]:
    """Получить фильм по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)) as cursor:
            row = await cursor.fetchone()
            return _row_to_movie(row) if row else None


async def get_movie_by_imdb_id(imdb_id: str) -> Optional[Movie]:
    """Получить фильм по IMDb ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT * FROM movies WHERE imdb_id = ?", (imdb_id,)) as cursor:
            row = await cursor.fetchone()
            return _row_to_movie(row) if row else None


async def add_movie(movie: MovieBase, source: str = "personal") -> Movie:
    """Добавить фильм в базу"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO movies (
                imdb_id, title, original_title, year, genres, description,
                plot, cast, director, poster_url, imdb_rating, awards, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            source
        ))
        await db.commit()
        movie_id = cursor.lastrowid
        return await get_movie_by_id(movie_id)


async def update_movie(movie_id: int, is_watched: bool) -> Optional[Movie]:
    """Обновить статус просмотра фильма"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE movies SET is_watched = ? WHERE id = ?",
            (is_watched, movie_id)
        )
        await db.commit()
        return await get_movie_by_id(movie_id)


async def delete_movie(movie_id: int) -> bool:
    """Удалить фильм из базы"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_unwatched_movies() -> list[Movie]:
    """Получить все непросмотренные фильмы для рекомендаций"""
    return await get_all_movies(is_watched=False)
