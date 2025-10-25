"""
Pydanticモデル
"""

from .user import (
    UserProfileResponse,
    UserProfileUpdate,
    UserInfo,
    # 後方互換（必要に応じて利用可）
    ProfileResponse,
    ProfileUpdate,
)
from .review import ReviewCreate, ReviewResponse
from .plan import (
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanCreate,
    PlanListResponse,
    PlanResponse,
    TransportMode,
)
from .match import MatchResponse
from .store import StoreSummary

__all__ = [
    "UserProfileResponse",
    "UserProfileUpdate",
    # 互換用エクスポート
    "ProfileResponse",
    "ProfileUpdate",
    "UserInfo",
    "ReviewCreate",
    "ReviewResponse",
    "PlanGenerateRequest",
    "PlanGenerateResponse",
    "PlanCreate",
    "PlanListResponse",
    "PlanResponse",
    "TransportMode",
    "MatchResponse",
    "StoreSummary",
]
