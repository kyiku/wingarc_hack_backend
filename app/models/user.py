"""
User-related Pydantic models.

Naming follows API spec: UserProfileResponse, UserProfileUpdate.
"""

from __future__ import annotations

from typing import Optional

import re
import unicodedata

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserProfileResponse(BaseModel):
    """Response model for GET /users/me."""

    id: str = Field(description="Supabase user UUID")
    email: EmailStr = Field(description="User email from auth.users")
    nickname: Optional[str] = Field(default=None, description="Public nickname")


class UserProfileUpdate(BaseModel):
    """Request body for updating the user's profile (nickname only)."""

    nickname: str = Field(min_length=1, max_length=50, description="New nickname")

    @field_validator("nickname")
    @classmethod
    def validate_and_normalize_nickname(cls, v: str) -> str:
        # Normalize to NFKC to avoid visually confusable variants
        v = unicodedata.normalize("NFKC", v)
        # Trim surrounding whitespace
        v = v.strip()
        if not v:
            raise ValueError("nickname must not be empty or whitespace only")
        # Disallow control characters
        if re.search(r"[\x00-\x1F\x7F]", v):
            raise ValueError("nickname must not contain control characters")
        return v
