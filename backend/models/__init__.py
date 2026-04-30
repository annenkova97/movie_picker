from backend.models.movie import (
    Movie,
    MovieBase,
    MovieCreate,
    MovieUpdate,
    RecommendationRequest,
    RecommendationResponse,
    OMDBSearchResult,
    MoviePreview,
    BulkImportItem,
    BulkImportRequest,
)
from backend.models.instagram import InstagramImportRequest
from backend.models.telegram import TelegramImportRequest
from backend.models.share import SharedListCreateRequest, SharedListResponse
from backend.models.user import (
    User,
    UserCreate,
    UserLogin,
    GoogleLogin,
    AuthResponse,
)

__all__ = [
    "Movie",
    "MovieBase",
    "MovieCreate",
    "MovieUpdate",
    "RecommendationRequest",
    "RecommendationResponse",
    "OMDBSearchResult",
    "MoviePreview",
    "BulkImportItem",
    "BulkImportRequest",
    "InstagramImportRequest",
    "TelegramImportRequest",
    "SharedListCreateRequest",
    "SharedListResponse",
    "User",
    "UserCreate",
    "UserLogin",
    "GoogleLogin",
    "AuthResponse",
]
