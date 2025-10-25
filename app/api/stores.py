"""
Stores API endpoints.

Currently provides a nearby local stores search using Google Places
with basic chain-store filtering.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.models.store import StoreSummary
from app.services.google_places import search_nearby_local_stores


router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("/nearby", response_model=List[StoreSummary])
def get_nearby_stores(
    lat: float = Query(..., description="Center latitude", ge=-90.0, le=90.0),
    lng: float = Query(..., description="Center longitude", ge=-180.0, le=180.0),
    radius_m: int = Query(1000, description="Search radius in meters (<= 50000)", ge=1, le=50000),
    limit: int = Query(20, description="Max number of results", ge=1, le=50),
) -> List[StoreSummary]:
    """Search for nearby non-chain local stores.

    Notes:
        - Requires ``GOOGLE_PLACES_API_KEY`` to call live Google Places.
          If missing, returns deterministic stub results for development.
        - ``has_reviews`` and ``is_recommended`` are placeholders until DB is integrated.
    """

    try:
        stores = search_nearby_local_stores(
            latitude=lat, longitude=lng, radius_m=radius_m, max_results=limit
        )
        return stores
    except HTTPException:
        raise
    except Exception as exc:
        # Convert any unexpected error into a 500 with a concise message.
        raise HTTPException(status_code=500, detail=f"Failed to search nearby stores: {exc}")

