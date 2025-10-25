"""
Profile service backed by Supabase.

Provides helpers to fetch the authenticated user from a Bearer token and
read/update the corresponding ``profiles`` table record.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.models.user import UserProfileResponse
from app.services.supabase_client import get_client


class NotConfiguredError(Exception):
    """Raised when Supabase is not configured/available."""


class AuthError(Exception):
    """Raised on authentication/authorization errors."""


def _require_client():
    client = get_client()
    if client is None:
        raise NotConfiguredError("Supabase client is not configured. Set SUPABASE_URL/KEY.")
    return client


def _get_auth_user(access_token: str) -> Dict[str, Any]:
    """Return auth user dict from Supabase for the given token."""

    client = _require_client()
    try:
        # supabase-py v2 returns a response object with a ``user`` attribute
        # which may be a dict-like structure. We normalize to dict.
        resp = client.auth.get_user(access_token)
        user = getattr(resp, "user", None) or getattr(resp, "data", None) or None
        if user is None:
            # Some versions expose it as resp.user
            raise AuthError("No user found for provided token")
        # Ensure we can access fields in a dict-like manner
        if hasattr(user, "model_dump"):
            user = user.model_dump()  # pydantic model in newer SDKs
        return dict(user)
    except AuthError:
        raise
    except Exception as exc:  # Broadly catch and map to AuthError for the API layer
        raise AuthError(f"Failed to validate token: {exc}")


def _try_rpc_get_me_profile(access_token: str) -> Optional[UserProfileResponse]:
    """Attempt to fetch profile via DB-side join RPC if available.

    Expects a SQL function: public.get_me_profile() returning (id uuid, email text, nickname text).
    Returns None if the RPC is not available or fails. Falls back to SDK path.
    """

    client = _require_client()
    try:
        # Ensure PostgREST queries use the end-user token so auth.uid() works.
        postgrest = getattr(client, "postgrest", None)
        if postgrest and hasattr(postgrest, "auth"):
            try:
                postgrest.auth(access_token)
            except Exception:
                pass

        resp = client.rpc("get_me_profile").execute()
        data = getattr(resp, "data", None)
        if not data:
            return None
        row = data[0] if isinstance(data, list) and data else data
        uid = row.get("id")
        email = row.get("email")
        nickname = row.get("nickname")
        if uid and email:
            return UserProfileResponse(id=str(uid), email=str(email), nickname=nickname)
        return None
    except Exception:
        return None


def _get_profile_nickname(user_id: str) -> Optional[str]:
    """Fetch nickname from ``profiles`` table, or ``None`` if not set."""

    client = _require_client()
    try:
        query = (
            client.table("profiles")
            .select("id,nickname")
            .eq("id", user_id)
            .single()
        )
        resp = query.execute()
        data = getattr(resp, "data", None)
        if not data:
            return None
        return data.get("nickname")
    except Exception:
        # If the row doesn't exist or any error occurs, treat as no nickname yet.
        return None


def _upsert_profile_nickname(user_id: str, nickname: str) -> None:
    """Upsert nickname for the given user id in ``profiles`` table."""

    client = _require_client()
    payload = {"id": user_id, "nickname": nickname}
    try:
        client.table("profiles").upsert(payload).execute()
    except Exception as exc:
        raise RuntimeError(f"Failed to update profile: {exc}")


def get_me_profile(access_token: str) -> UserProfileResponse:
    """Return the current authenticated user's profile."""
    # Prefer DB-side join via RPC if available.
    rpc_result = _try_rpc_get_me_profile(access_token)
    if rpc_result is not None:
        return rpc_result

    user = _get_auth_user(access_token)
    user_id = user.get("id") or user.get("user", {}).get("id")
    email = user.get("email") or user.get("user", {}).get("email")
    if not user_id or not email:
        raise AuthError("Invalid auth user payload")
    nickname = _get_profile_nickname(user_id)
    return UserProfileResponse(id=str(user_id), email=str(email), nickname=nickname)


def update_me_nickname(access_token: str, *, nickname: str) -> UserProfileResponse:
    """Update the current user's nickname and return the updated profile."""
    # Try RPC-based update if available: public.update_my_nickname(new_nickname text)
    client = _require_client()
    try:
        postgrest = getattr(client, "postgrest", None)
        if postgrest and hasattr(postgrest, "auth"):
            try:
                postgrest.auth(access_token)
            except Exception:
                pass
        resp = client.rpc("update_my_nickname", {"new_nickname": nickname}).execute()
        data = getattr(resp, "data", None)
        if data:
            row = data[0] if isinstance(data, list) and data else data
            uid = row.get("id")
            email = row.get("email")
            nk = row.get("nickname")
            if uid and email:
                return UserProfileResponse(id=str(uid), email=str(email), nickname=nk)
    except Exception:
        pass

    user = _get_auth_user(access_token)
    user_id = user.get("id") or user.get("user", {}).get("id")
    email = user.get("email") or user.get("user", {}).get("email")
    if not user_id or not email:
        raise AuthError("Invalid auth user payload")
    _upsert_profile_nickname(str(user_id), nickname)
    return UserProfileResponse(id=str(user_id), email=str(email), nickname=nickname)
