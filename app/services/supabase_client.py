"""
Supabase client factory and helpers.

Creates a Supabase client using environment variables.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    from supabase import Client, create_client  # type: ignore
except Exception:  # pragma: no cover - optional import during local dev
    Client = object  # type: ignore
    create_client = None  # type: ignore


def is_configured() -> bool:
    """Return True if environment contains Supabase credentials."""

    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))


def get_client() -> Optional[Client]:
    """Instantiate and return a Supabase client or ``None`` if unavailable."""

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or create_client is None:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None

