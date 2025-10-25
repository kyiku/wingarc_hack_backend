"""
ユーザー関連のモデル
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class ProfileBase(BaseModel):
    """プロフィールの基底モデル"""
    nickname: str = Field(..., min_length=1, max_length=50, description="ユーザーのニックネーム")


class ProfileUpdate(BaseModel):
    """プロフィール更新リクエスト"""
    nickname: str = Field(..., min_length=1, max_length=50, description="新しいニックネーム")


class ProfileResponse(ProfileBase):
    """プロフィールレスポンス"""
    id: UUID
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserInfo(BaseModel):
    """現在のユーザー情報（認証用）"""
    id: str
    email: str
    user_metadata: dict = {}
