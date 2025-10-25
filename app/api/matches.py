"""
Matches API endpoints.
"""

from __future__ import annotations

from typing import List, Optional, Literal

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.models.match import MatchResponse
from app.services.match_service import list_matches


router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get("", response_model=List[MatchResponse])
def get_matches(
    from_: Optional[datetime] = Query(None, alias="from", description="Include matches at/after this datetime (ISO 8601)"),
    to: Optional[datetime] = Query(None, alias="to", description="Include matches at/before this datetime (ISO 8601)"),
    only: Optional[Literal["past", "future"]] = Query(
        None,
        description="Optional time filter: 'past' (<= now) or 'future' (>= now)",
    ),
) -> List[MatchResponse]:
    """Return registered matches in ascending date order.

    Optional filters:
        - from (ISO 8601): lower bound (inclusive) for match_datetime
        - to (ISO 8601): upper bound (inclusive) for match_datetime
    """
    # Optional quick filter for past/future relative to current UTC time
    now = datetime.now(timezone.utc)
    if only == "future":
        if from_ is None or from_ < now:
            from_ = now
    elif only == "past":
        if to is None or to > now:
            to = now

    try:
        return list_matches(start=from_, end=to)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch matches: {exc}")
