from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Optional
from backend.auth import get_current_user_optional
from backend.models import RecommendationRequest, RecommendationResponse, User, Movie
from backend.rate_limit import limiter, user_or_ip_key
from backend.services import llm_service
from backend import database as db

router = APIRouter(prefix="/api/recommend", tags=["recommendations"])

# Upper bound on how many films we hand the LLM. Keeps the prompt (and cost)
# bounded even for a user with a large saved library plus the full awards
# catalog. The user's own movies are always kept; awards fill the remainder.
MAX_CANDIDATES = 80


def _merge_with_awards(saved: list[Movie], awards: list[Movie]) -> list[Movie]:
    """Combine the user's saved movies with the global award-winners catalog.

    Deduplicated by ``imdb_id`` — the user's own copy always wins so we keep
    their ``is_watched`` flag and real id. Capped at ``MAX_CANDIDATES``.
    """
    seen = {m.imdb_id for m in saved}
    extra = [a for a in awards if a.imdb_id not in seen]
    room = max(0, MAX_CANDIDATES - len(saved))
    return saved + extra[:room]


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

    К кандидатам всегда подмешиваются фильмы-победители премий, чтобы подбор
    под настроение мог предложить и признанное кино из каталога наград.
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

    # Always mix in award-winning films (Oscar, Cannes, Golden Globe…) so a
    # mood-based pick can surface acclaimed cinema the user hasn't saved yet.
    awards = await db.get_awards()
    candidates = _merge_with_awards(movies, awards)

    if not candidates:
        return RecommendationResponse(
            movies=[],
            explanation="В вашем списке пока нет фильмов. Сохраните хотя бы один — тогда смогу подобрать."
        )

    recommended_ids, explanation = await llm_service.recommend_movies(
        payload.query,
        candidates,
        max_recommendations=3
    )

    recommended_movies = [m for m in candidates if m.id in recommended_ids]

    id_to_order = {id_: idx for idx, id_ in enumerate(recommended_ids)}
    recommended_movies.sort(key=lambda m: id_to_order.get(m.id, 999))

    return RecommendationResponse(
        movies=recommended_movies,
        explanation=explanation
    )
