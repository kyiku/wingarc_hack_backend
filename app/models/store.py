"""
Store-related Pydantic models.

These models shape the API responses for store endpoints.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.review import ReviewResponse


class StoreSummary(BaseModel):
    """A concise representation of a store for list views.

    Notes:
        - ``id`` represents the internal store UUID in our DB. It may be ``None``
          if the store is not yet persisted. ``google_place_id`` is always present.
    """

    id: Optional[str] = Field(default=None, description="Internal store UUID (if persisted)")
    google_place_id: str = Field(description="Google Places place_id")
    name: str = Field(description="Store display name")
    latitude: float = Field(description="Latitude in WGS84")
    longitude: float = Field(description="Longitude in WGS84")
    has_reviews: bool = Field(default=False, description="True if our app has user reviews")
    is_recommended: bool = Field(default=False, description="True if there is a player recommendation")


class PlayerRecommendation(BaseModel):
    """選手のおすすめ情報"""

    id: str = Field(description="おすすめID (UUID)")
    player_name: str = Field(description="選手名")
    comment: str = Field(description="おすすめコメント")

    model_config = {"from_attributes": True}


class StoreDetail(BaseModel):
    """店舗の詳細情報（口コミと選手おすすめ含む）"""

    id: str = Field(description="店舗ID (UUID)")
    google_place_id: str = Field(description="Google Places place_id")
    name: str = Field(description="店舗名")
    address: str = Field(description="住所")
    latitude: float = Field(description="緯度 (WGS84)")
    longitude: float = Field(description="経度 (WGS84)")
    opening_hours: Optional[List[str]] = Field(default=None, description="営業時間（文字列配列）")
    reviews: List[ReviewResponse] = Field(default_factory=list, description="口コミ一覧")
    recommendations: List[PlayerRecommendation] = Field(default_factory=list, description="選手のおすすめ一覧")

    model_config = {"from_attributes": True}


# Rebuild model to resolve forward references
StoreDetail.model_rebuild()
