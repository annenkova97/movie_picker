from backend.models.movie import (
    Movie,
    MovieBase,
    MovieCreate,
    MovieUpdate,
    RecommendationRequest,
    RecommendationResponse,
    OMDBSearchResult
)
from backend.models.instagram import InstagramImportRequest

__all__ = [
    "Movie",
    "MovieBase",
    "MovieCreate",
    "MovieUpdate",
    "RecommendationRequest",
    "RecommendationResponse",
    "OMDBSearchResult",
    "InstagramImportRequest"
]
