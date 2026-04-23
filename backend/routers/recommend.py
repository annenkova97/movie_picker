from fastapi import APIRouter, Depends
from backend.auth import get_current_user
from backend.models import RecommendationRequest, RecommendationResponse, User
from backend.services import llm_service
from backend import database as db

router = APIRouter(prefix="/api/recommend", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    current_user: User = Depends(get_current_user),
):
    """Рекомендации по библиотеке текущего пользователя."""
    if request.include_watched:
        movies = await db.get_all_movies(user_id=current_user.id)
    else:
        movies = await db.get_unwatched_movies(user_id=current_user.id)

    if not movies:
        return RecommendationResponse(
            movies=[],
            explanation="В вашем списке пока нет непросмотренных фильмов. Добавьте фильмы, чтобы получить рекомендации."
        )

    recommended_ids, explanation = await llm_service.recommend_movies(
        request.query,
        movies,
        max_recommendations=3
    )

    recommended_movies = [m for m in movies if m.id in recommended_ids]

    id_to_order = {id_: idx for idx, id_ in enumerate(recommended_ids)}
    recommended_movies.sort(key=lambda m: id_to_order.get(m.id, 999))

    return RecommendationResponse(
        movies=recommended_movies,
        explanation=explanation
    )
