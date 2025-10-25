"""
Service for fetching match information from Supabase with a dev-friendly stub fallback.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.models.match import MatchResponse
from app.services.supabase_client import get_client


def _stub_matches() -> List[MatchResponse]:
    now = datetime.now(timezone.utc)
    return [
        MatchResponse(
            id="match-stub-1",
            match_datetime=now + timedelta(days=1),
            opponent="ヴァンラーレ八戸",
            venue_name="ミクニワールドスタジアム北九州",
            venue_latitude=33.885,
            venue_longitude=130.880,
        )
    ]


def list_matches(*, start: Optional[datetime] = None, end: Optional[datetime] = None) -> List[MatchResponse]:
    """Return matches ordered by datetime ascending with optional date-range filter.

    Args:
        start: Include matches whose ``match_datetime`` is >= this value.
        end: Include matches whose ``match_datetime`` is <= this value.

    Falls back to a deterministic stub when Supabase is not configured or on errors.
    """

    client = get_client()
    if client is None:
        # Filter stub data locally
        items = _stub_matches()
        if start is not None:
            items = [m for m in items if m.match_datetime >= start]
        if end is not None:
            items = [m for m in items if m.match_datetime <= end]
        return items

    try:
        query = (
            client.table("matches")
            .select("id, match_datetime, opponent, venue_name, venue_latitude, venue_longitude")
        )
        if start is not None:
            query = query.gte("match_datetime", start.isoformat())
        if end is not None:
            query = query.lte("match_datetime", end.isoformat())
        query = query.order("match_datetime", desc=False)
        resp = query.execute()
        data = getattr(resp, "data", None) or []
        results: List[MatchResponse] = []
        for row in data:
            try:
                results.append(
                    MatchResponse(
                        id=str(row.get("id")),
                        match_datetime=row.get("match_datetime"),
                        opponent=str(row.get("opponent")),
                        venue_name=str(row.get("venue_name")),
                        venue_latitude=float(row.get("venue_latitude")),
                        venue_longitude=float(row.get("venue_longitude")),
                    )
                )
            except Exception:
                # Skip malformed rows
                continue
        return results
    except Exception:
        items = _stub_matches()
        if start is not None:
            items = [m for m in items if m.match_datetime >= start]
        if end is not None:
            items = [m for m in items if m.match_datetime <= end]
        return items
