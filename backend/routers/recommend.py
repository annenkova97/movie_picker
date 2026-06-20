import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Optional
from backend.auth import get_current_user_optional
from backend.models import RecommendationRequest, RecommendationResponse, User, Movie
from backend.rate_limit import limiter, user_or_ip_key
from backend.services import llm_service
from backend.services.availability import get_availability, is_available_on
from backend import database as db

router = APIRouter(prefix="/api/recommend", tags=["recommendations"])

# Upper bound on how many films we hand the LLM. Keeps the prompt (and cost)
# bounded even for a user with a large saved library plus the full awards
# catalog. The user's own movies are always kept; awards fill the remainder.
MAX_CANDIDATES = 80

# Сколько фильмов финально показываем. При работе с доступностью просим у LLM
# с запасом (есть из чего отфильтровать / что поднять выше), потом обрезаем.
MAX_RECOMMENDATIONS = 3
MAX_RECOMMENDATIONS_AVAIL = 6


async def _resolve_avail_prefs(
    payload: RecommendationRequest, current_user: Optional[User]
) -> tuple[Optional[str], list[int], bool]:
    """Регион/сервисы/флаг фильтра: payload приоритетнее, иначе из настроек.

    Возвращает ``(region, services, only_available)``. ``only_available``
    включается только когда есть сервисы — иначе фильтровать не по чему."""
    region = payload.region
    services = payload.services
    if current_user is not None:
        saved = await db.get_user_settings(current_user.id)
        if not region:
            region = saved["region"]
        if services is None:
            services = saved["streaming_services"]
    services = services or []
    only_available = payload.only_available and bool(services)
    return (region.upper() if region else None), services, only_available


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

    region, services, only_available = await _resolve_avail_prefs(payload, current_user)
    # С запасом просим только когда реально будем фильтровать/переупорядочивать
    # (есть и регион, и сервисы). Если регион есть, а сервисов нет — доступность
    # только для бейджей, выдачу не трогаем, поэтому ровно 3, чтобы объяснение
    # LLM совпадало с показанными фильмами.
    max_recs = MAX_RECOMMENDATIONS_AVAIL if (region and services) else MAX_RECOMMENDATIONS

    recommended_ids, explanation = await llm_service.recommend_movies(
        payload.query,
        candidates,
        max_recommendations=max_recs,
    )

    ordered = [m for m in candidates if m.id in recommended_ids]
    id_to_order = {id_: idx for idx, id_ in enumerate(recommended_ids)}
    ordered.sort(key=lambda m: id_to_order.get(m.id, 999))

    availability_map: dict[str, dict] = {}
    if region:
        # Доступность тянем только для рекомендованных (≤6), а не для всех 80
        # кандидатов — иначе шквал запросов в TMDb. Параллельно, кэш внутри.
        resolved = await asyncio.gather(
            *(get_availability(m.imdb_id, region) for m in ordered)
        )
        for movie, av in zip(ordered, resolved):
            if av is not None:
                availability_map[str(movie.id)] = av

        if services:
            available = {
                m.id: is_available_on(availability_map.get(str(m.id)), services)
                for m in ordered
            }
            if only_available:
                filtered = [m for m in ordered if available[m.id]]
                if filtered:
                    ordered = filtered
                else:
                    # Edge case: фильтр всё вычистил — не отдаём пустой экран,
                    # показываем лучшее из подходящего с честной пометкой.
                    explanation = (
                        "Ничего из доступного на твоих сервисах не нашлось — "
                        "вот лучшее из подходящего:\n\n" + explanation
                    )
            else:
                # Не фильтруем, но доступное поднимаем выше (стабильно — внутри
                # групп сохраняется порядок LLM).
                ordered.sort(key=lambda m: 0 if available[m.id] else 1)

    ordered = ordered[:MAX_RECOMMENDATIONS]
    returned_ids = {str(m.id) for m in ordered}
    availability_map = {k: v for k, v in availability_map.items() if k in returned_ids}

    return RecommendationResponse(
        movies=ordered,
        explanation=explanation,
        availability=availability_map,
    )
