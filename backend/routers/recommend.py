from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Optional
from backend.auth import get_current_user_optional
from backend.models import RecommendationRequest, RecommendationResponse, User
from backend.rate_limit import limiter, user_or_ip_key
from backend.services import llm_service
from backend import database as db

router = APIRouter(prefix="/api/recommend", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
@limiter.limit("30/hour", key_func=user_or_ip_key)
async def get_recommendations(
    request: Request,
    payload: RecommendationRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Рекомендации.

    Источник библиотеки выбирается так:
    - если в payload передан ``library`` — используем его (guest-режим, auth не нужен);
    - иначе если есть auth — берём библиотеку пользователя из БД;
    - иначе возвращаем 401.
    """
    if payload.library is not None:
        movies = payload.library
        if not payload.include_watched:
            movies = [m for m in movies if not m.is_watched]
    elif current_user is not None:
        if payload.include_watched:
            movies = await db.get_all_movies(user_id=current_user.id)
        else:
            movies = await db.get_unwatched_movies(user_id=current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Передай библиотеку в поле 'library' или войди в аккаунт",
        )

    if not movies:
        return RecommendationResponse(
            movies=[],
            explanation="В вашем списке пока нет фильмов. Сохраните хотя бы один — тогда смогу подобрать."
        )

    recommended_ids, explanation = await llm_service.recommend_movies(
        payload.query,
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
