"""
Store-related Pydantic models.

These models shape the API responses for store endpoints.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


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

