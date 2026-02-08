import anthropic
from typing import Optional
from backend.config import ANTHROPIC_API_KEY
from backend.models.movie import Movie


class LLMService:
    """Сервис для работы с Claude API"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def generate_short_description(self, plot: str, title: str) -> str:
        """Генерация краткого описания фильма на русском"""
        if not plot:
            return ""

        prompt = f"""Напиши очень краткое описание фильма "{title}" на русском языке (2-3 предложения).
Опиши главную идею и атмосферу фильма, не раскрывая спойлеров.

Полный сюжет для анализа:
{plot}

Ответь только описанием, без вступлений и пояснений."""

        message = self.client.messages.create(
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

        message = self.client.messages.create(
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
