"""
ユーザー関連のモデル
"""

from pydantic import BaseModel, Field
from uuid import UUID


class ProfileBase(BaseModel):
    """プロフィールの基底モデル"""
    nickname: str = Field(..., min_length=1, max_length=50, description="ユーザーのニックネーム")


class UserProfileUpdate(BaseModel):
    """プロフィール更新リクエスト"""
    nickname: str = Field(..., min_length=1, max_length=50, description="新しいニックネーム")


class UserProfileResponse(ProfileBase):
    """プロフィールレスポンス（id, email, nickname のみ）"""
    id: UUID
    email: str = Field(description="ユーザーのメールアドレス")

    model_config = {"from_attributes": True}


class UserInfo(BaseModel):
    """現在のユーザー情報（認証用）"""
    id: str
    email: str
    user_metadata: dict = {}

# 後方互換エイリアス（既存参照のため）
ProfileResponse = UserProfileResponse
ProfileUpdate = UserProfileUpdate
