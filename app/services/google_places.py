"""
Google Places service wrapper.

Provides a thin abstraction over ``googlemaps`` to search for nearby stores
and adapt results to our application models.
"""

from __future__ import annotations

import os
import logging
from typing import Iterable, List, Optional

try:
    import googlemaps  # type: ignore
    try:  # narrow exceptions when possible
        from googlemaps.exceptions import ApiError, TransportError, Timeout  # type: ignore
    except Exception:  # pragma: no cover - optional import variants
        ApiError = TransportError = Timeout = Exception  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    googlemaps = None  # type: ignore
    ApiError = TransportError = Timeout = Exception  # type: ignore

from app.models.store import StoreSummary
from app.services.chain_filter import (
    filter_out_chain_items,
    filter_out_chain_items_dyn,
    get_dynamic_chain_keywords,
)

logger = logging.getLogger(__name__)

def _to_store_summary(place: dict) -> Optional[StoreSummary]:
    """Convert a Google Places ``place`` dict to ``StoreSummary``.

    Returns ``None`` if essential fields are missing or if it's a hotel/lodging.
    """

    try:
        place_id = place.get("place_id")
        name = place.get("name")
        geom = place.get("geometry", {})
        loc = geom.get("location", {})
        lat = float(loc.get("lat"))
        lng = float(loc.get("lng"))
    except (TypeError, ValueError):
        return None

    if not place_id or not name:
        return None

    # ホテルや宿泊施設を除外
    types = place.get("types", [])
    if isinstance(types, list):
        lodging_types = {"lodging", "hotel", "motel", "hostel", "guest_house"}
        if any(t in lodging_types for t in types):
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
    # 環境変数の値から不要な空白・改行を削除
    if api_key:
        api_key = api_key.strip()

    # デバッグログ追加
    logger.info(f"Google Places API検索: lat={latitude}, lng={longitude}")
    logger.info(f"API Key exists: {bool(api_key)}")
    logger.info(f"googlemaps module available: {googlemaps is not None}")

    if api_key:
        # APIキーの最初の数文字だけをログに出力（セキュリティのため）
        logger.info(f"API Key prefix: {api_key[:10]}...")

    # If googlemaps is not available or API key missing, return stub results.
    if not api_key:
        logger.warning("GOOGLE_PLACES_API_KEY not found - returning stub data")
        return _stub_results(latitude, longitude)[:max_results]

    if googlemaps is None:
        logger.warning("googlemaps module not available - returning stub data")
        return _stub_results(latitude, longitude)[:max_results]

    try:
        logger.info("Creating googlemaps client...")
        client = googlemaps.Client(key=api_key)
        logger.info("googlemaps client created successfully")

        # 複数のタイプで検索してマージ（より多くの飲食店を取得）
        search_types = ["restaurant", "cafe", "bar", "bakery"]
        all_results: List[dict] = []
        seen_place_ids: set = set()

        for place_type in search_types:
            try:
                logger.info(f"Searching for type: {place_type}")
                resp = client.places_nearby(
                    location=(latitude, longitude),
                    radius=radius_m,
                    type=place_type,
                )
                results_count = len(resp.get("results", []))
                logger.info(f"Found {results_count} results for {place_type}")

                for place in resp.get("results", []):
                    place_id = place.get("place_id")
                    if place_id and place_id not in seen_place_ids:
                        seen_place_ids.add(place_id)
                        all_results.append(place)
            except Exception as e:
                logger.warning(f"タイプ {place_type} の検索中にエラー: {e}")
                continue

        logger.info(f"Total unique places found: {len(all_results)}")

        results: Iterable[dict] = all_results

        # Filter out chain brands. Prefer DB-provided chain list when available.
        extra = []
        try:
            extra = get_dynamic_chain_keywords()
        except Exception:
            # 動的キーワード取得失敗はフィルタなしで継続
            logger.debug("動的チェーンキーワードの取得に失敗。静的フィルタにフォールバック")
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
    except (ApiError, TransportError, Timeout):
        logger.warning("Google Places APIエラー。スタブ結果にフォールバック")
        return _stub_results(latitude, longitude)[:max_results]
    except Exception:
        # On any other runtime error, fall back to stub to keep the endpoint robust.
        logger.exception("Google Places処理中に予期しないエラー")
        return _stub_results(latitude, longitude)[:max_results]

