"""
Store-related Pydantic models.

These models shape the API responses for store endpoints.
"""

from __future__ import annotations

from datetime import datetime
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
    """A player recommendation registered by club staff.

    Only the fields required by the API spec are exposed.
    """

    id: str = Field(description="Recommendation UUID")
    player_name: str = Field(description="Player name")
    comment: str = Field(description="Recommendation comment")

    model_config = {"from_attributes": True}


class StoreDetail(BaseModel):
    """Detailed store information with reviews and recommendations."""

    id: str = Field(description="Store UUID")
    google_place_id: str = Field(description="Google Places place_id")
    name: str = Field(description="Store display name")
    address: str = Field(description="Postal address")
    latitude: float = Field(description="Latitude in WGS84")
    longitude: float = Field(description="Longitude in WGS84")
    opening_hours: Optional[List[str]] = Field(default=None, description="Human-friendly opening hours")
    reviews: List[ReviewResponse] = Field(default_factory=list, description="User reviews for the store")
    recommendations: List[PlayerRecommendation] = Field(
        default_factory=list, description="Player recommendations for this store"
    )

    model_config = {"from_attributes": True}

