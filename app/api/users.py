"""
Users API endpoints: profile get/update.

Requires Authorization: Bearer <supabase_access_token> header.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.models.user import UserProfileResponse, UserProfileUpdate
from app.services.profile_service import (
    AuthError,
    NotConfiguredError,
    get_me_profile,
    update_me_nickname,
)


router = APIRouter(prefix="/users", tags=["Users"])


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    return token


def bearer_token_dependency(authorization: Optional[str] = Header(default=None)) -> str:
    return _extract_bearer_token(authorization)


@router.get("/me", response_model=UserProfileResponse)
def get_me(token: str = Depends(bearer_token_dependency)) -> UserProfileResponse:
    """Return the authenticated user's profile (id, email, nickname)."""

    try:
        return get_me_profile(token)
    except NotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get profile: {exc}")


@router.put("/me", response_model=UserProfileResponse)
def update_me(body: UserProfileUpdate, token: str = Depends(bearer_token_dependency)) -> UserProfileResponse:
    """Update the authenticated user's nickname and return the updated profile."""

    try:
        return update_me_nickname(token, nickname=body.nickname)
    except NotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update profile: {exc}")
