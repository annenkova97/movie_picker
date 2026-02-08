from fastapi import APIRouter
from backend.models import RecommendationRequest, RecommendationResponse, Movie
from backend.services import llm_service
from backend import database as db

router = APIRouter(prefix="/api/recommend", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Получить рекомендации на основе свободного запроса.
    Примеры запросов:
    - "что-то лёгкое"
    - "драма про семью"
    - "фильм с Бенедиктом Камбербэтчем"
    - "что-нибудь захватывающее, но не боевик"
    """
    # Получаем фильмы для рекомендаций
    if request.include_watched:
        movies = await db.get_all_movies()
    else:
        movies = await db.get_unwatched_movies()

    if not movies:
        return RecommendationResponse(
            movies=[],
            explanation="В вашем списке пока нет непросмотренных фильмов. Добавьте фильмы, чтобы получить рекомендации."
        )

    # Получаем рекомендации от LLM
    recommended_ids, explanation = await llm_service.recommend_movies(
        request.query,
        movies,
        max_recommendations=3
    )

    # Находим рекомендованные фильмы
    recommended_movies = [m for m in movies if m.id in recommended_ids]

    # Сортируем в порядке рекомендаций
    id_to_order = {id_: idx for idx, id_ in enumerate(recommended_ids)}
    recommended_movies.sort(key=lambda m: id_to_order.get(m.id, 999))

    return RecommendationResponse(
        movies=recommended_movies,
        explanation=explanation
    )
