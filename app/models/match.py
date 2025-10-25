"""
Match-related Pydantic models.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class MatchResponse(BaseModel):
    """Response model for a single match item."""

    id: str = Field(description="Match UUID")
    match_datetime: datetime = Field(description="Match kickoff datetime (ISO 8601)")
    opponent: str = Field(description="Opponent team name")
    venue_name: str = Field(description="Venue display name")
    venue_latitude: float = Field(description="Venue latitude (WGS84)")
    venue_longitude: float = Field(description="Venue longitude (WGS84)")

