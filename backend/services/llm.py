import anthropic
from typing import Optional
from backend.config import ANTHROPIC_API_KEY
from backend.models.movie import Movie
from backend.models.book import Book


class LLMService:
    """Сервис для работы с Claude API"""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"

    async def translate_movie_title(self, title: str) -> str:
        """Перевод названия фильма с русского на английский для поиска в OMDB."""
        prompt = f"""Переведи название фильма на английский язык для поиска в базе данных OMDB.
Верни ТОЛЬКО английское название фильма, без кавычек, без пояснений, без лишних слов.
Если название уже на английском — верни его без изменений.

Название: {title}"""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip().strip('"').strip("'")

    async def translate_plot(self, plot: str, title: str) -> str:
        """Перевод сюжета на русский с сохранением фактов и тона."""
        if not plot:
            return ""

        prompt = f"""Переведи на русский язык описание сюжета фильма "{title}".
Сохрани факты (имена, места, сюжетные повороты), не добавляй ничего от себя,
не раскрывай спойлеров сверх того, что есть в оригинале. Не используй кавычки-ёлочки.

Оригинал:
{plot}

Ответь только переводом, без вступлений и пояснений."""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    async def generate_short_description(self, plot: str, title: str) -> str:
        """Генерация краткого описания фильма на русском"""
        if not plot:
            return ""

        prompt = f"""Напиши очень краткое описание фильма "{title}" на русском языке (2-3 предложения).
Опиши главную идею и атмосферу фильма, не раскрывая спойлеров.

Полный сюжет для анализа:
{plot}

Ответь только описанием, без вступлений и пояснений."""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text.strip()

    async def recommend_movies(
        self,
        user_query: str,
        movies: list[Movie],
        max_recommendations: int = 3
    ) -> tuple[list[int], str]:
        """
        Рекомендация фильмов на основе запроса пользователя.
        Возвращает список ID фильмов и объяснение.
        """
        if not movies:
            return [], "В вашем списке пока нет фильмов для рекомендаций."

        # Формируем описание фильмов для промпта
        movies_info = []
        for m in movies:
            info = f"[ID:{m.id}] «{m.title}» ({m.year or 'год неизвестен'})"
            if m.genres:
                info += f" — {', '.join(m.genres)}"
            if m.cast:
                info += f" | Актёры: {', '.join(m.cast[:3])}"
            if m.description:
                info += f" | {m.description}"
            elif m.plot:
                info += f" | {m.plot[:200]}..."
            movies_info.append(info)

        movies_text = "\n".join(movies_info)

        prompt = f"""Ты — помощник по выбору фильмов. Пользователь хочет посмотреть что-то из своего списка.

Запрос пользователя: "{user_query}"

Список фильмов пользователя (непросмотренные):
{movies_text}

Выбери от 1 до {max_recommendations} наиболее подходящих фильмов.
Отвечай строго в формате:
РЕКОМЕНДАЦИИ: [ID1, ID2, ID3]
ОБЪЯСНЕНИЕ: Почему эти фильмы подходят под запрос (2-3 предложения на русском).

Если ни один фильм не подходит, напиши:
РЕКОМЕНДАЦИИ: []
ОБЪЯСНЕНИЕ: Причина, почему ничего не подходит."""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()
        return self._parse_recommendation_response(response_text)

    async def recommend_books(
        self,
        user_query: str,
        books: list[Book],
        max_recommendations: int = 3
    ) -> tuple[list[int], str]:
        """Подбор книги под настроение. Возвращает список ID книг и объяснение.

        Делит парсер ответа с ``recommend_movies`` — формат вывода идентичный.
        """
        if not books:
            return [], "В вашем списке пока нет книг для рекомендаций."

        books_info = []
        for b in books:
            info = f"[ID:{b.id}] «{b.title}» ({b.year or 'год неизвестен'})"
            if b.authors:
                info += f" — {', '.join(b.authors[:2])}"
            if b.subjects:
                info += f" | Темы: {', '.join(b.subjects[:3])}"
            if b.description:
                info += f" | {b.description[:200]}"
            books_info.append(info)

        books_text = "\n".join(books_info)

        prompt = f"""Ты — помощник по выбору книг. Пользователь хочет почитать что-то из своего списка.

Запрос пользователя: "{user_query}"

Список книг пользователя (непрочитанные):
{books_text}

Выбери от 1 до {max_recommendations} наиболее подходящих книг.
Отвечай строго в формате:
РЕКОМЕНДАЦИИ: [ID1, ID2, ID3]
ОБЪЯСНЕНИЕ: Почему эти книги подходят под запрос (2-3 предложения на русском).

Если ни одна книга не подходит, напиши:
РЕКОМЕНДАЦИИ: []
ОБЪЯСНЕНИЕ: Причина, почему ничего не подходит."""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()
        return self._parse_recommendation_response(response_text)

    def _parse_recommendation_response(self, response: str) -> tuple[list[int], str]:
        """Парсинг ответа LLM с рекомендациями"""
        movie_ids = []
        explanation = ""

        lines = response.split("\n")
        for line in lines:
            if line.startswith("РЕКОМЕНДАЦИИ:"):
                # Извлекаем список ID
                ids_part = line.replace("РЕКОМЕНДАЦИИ:", "").strip()
                # Убираем скобки и парсим числа
                ids_part = ids_part.strip("[]")
                if ids_part:
                    try:
                        movie_ids = [int(x.strip()) for x in ids_part.split(",") if x.strip()]
                    except ValueError:
                        movie_ids = []
            elif line.startswith("ОБЪЯСНЕНИЕ:"):
                explanation = line.replace("ОБЪЯСНЕНИЕ:", "").strip()

        # Если объяснение на следующих строках
        if not explanation:
            for i, line in enumerate(lines):
                if line.startswith("ОБЪЯСНЕНИЕ:"):
                    explanation = "\n".join(lines[i:]).replace("ОБЪЯСНЕНИЕ:", "").strip()
                    break

        return movie_ids, explanation


# Синглтон для использования в приложении
llm_service = LLMService()
