"""
Google Places service wrapper.

Provides a thin abstraction over ``googlemaps`` to search for nearby stores
and adapt results to our application models.
"""

from __future__ import annotations

import os
from typing import Iterable, List, Optional

try:
    import googlemaps  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    googlemaps = None  # type: ignore

from app.models.store import StoreSummary
from app.services.chain_filter import (
    filter_out_chain_items,
    filter_out_chain_items_dyn,
    get_dynamic_chain_keywords,
)


def _to_store_summary(place: dict) -> Optional[StoreSummary]:
    """Convert a Google Places ``place`` dict to ``StoreSummary``.

    Returns ``None`` if essential fields are missing.
    """

    try:
        place_id = place.get("place_id")
        name = place.get("name")
        geom = place.get("geometry", {})
        loc = geom.get("location", {})
        lat = float(loc.get("lat"))
        lng = float(loc.get("lng"))
    except Exception:
        return None

    if not place_id or not name:
        return None

    return StoreSummary(
        id=None,
        google_place_id=str(place_id),
        name=str(name),
        latitude=lat,
        longitude=lng,
        has_reviews=False,  # Will be set using our DB once integrated
        is_recommended=False,  # Will be set using our DB once integrated
    )


def _stub_results(lat: float, lng: float) -> List[StoreSummary]:
    """Return deterministic stub results when Google API is unavailable.

    The results are offset slightly around the given coordinates for realism.
    """

    return [
        StoreSummary(
            id=None,
            google_place_id="stub_1",
            name="ローカル居酒屋 A",
            latitude=lat + 0.0015,
            longitude=lng + 0.0015,
        ),
        StoreSummary(
            id=None,
            google_place_id="stub_2",
            name="町の定食屋 B",
            latitude=lat - 0.0012,
            longitude=lng + 0.0008,
        ),
        StoreSummary(
            id=None,
            google_place_id="stub_3",
            name="喫茶ローカル C",
            latitude=lat + 0.0007,
            longitude=lng - 0.0011,
        ),
    ]


def search_nearby_local_stores(
    *,
    latitude: float,
    longitude: float,
    radius_m: int = 1000,
    max_results: int = 20,
) -> List[StoreSummary]:
    """Search nearby stores using Google Places, filtering out chain brands.

    Args:
        latitude: Center latitude.
        longitude: Center longitude.
        radius_m: Search radius in meters (max 50,000 by Google API).
        max_results: Upper bound on number of items to return.

    Returns:
        A list of ``StoreSummary`` items.
    """

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")

    # If googlemaps is not available or API key missing, return stub results.
    if not api_key or googlemaps is None:
        return _stub_results(latitude, longitude)[:max_results]

    try:
        client = googlemaps.Client(key=api_key)
        # Use a broad category; later we can refine keywords/types.
        resp = client.places_nearby(
            location=(latitude, longitude),
            radius=radius_m,
            type="restaurant",
        )
        results: Iterable[dict] = resp.get("results", [])

        # Filter out chain brands. Prefer DB-provided chain list when available.
        extra = []
        try:
            extra = get_dynamic_chain_keywords()
        except Exception:
            extra = []
        if extra:
            filtered = filter_out_chain_items_dyn(
                results, lambda p: str(p.get("name", "")), extra_keywords=extra
            )
        else:
            filtered = filter_out_chain_items(results, lambda p: str(p.get("name", "")))

        # Map to StoreSummary and drop invalid entries.
        summaries = [_to_store_summary(p) for p in filtered]
        summaries = [s for s in summaries if s is not None]
        return summaries[:max_results]
    except Exception:
        # On any API/runtime error, fall back to stub to keep the endpoint robust.
        return _stub_results(latitude, longitude)[:max_results]

