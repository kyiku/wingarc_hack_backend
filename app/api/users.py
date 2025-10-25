"""
ユーザー関連のAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.auth import get_current_user
from app.database import get_supabase
from app.models.user import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    現在ログイン中のユーザーのプロフィール情報を取得

    認証が必要なエンドポイントです。

    Returns:
        ProfileResponse: ユーザーのプロフィール情報
    """
    user_id = current_user["id"]

    # profilesテーブルからユーザープロフィールを取得
    response = supabase.table("profiles").select("*").eq("id", user_id).execute()

    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プロフィールが見つかりません",
        )

    profile = response.data[0]
    return ProfileResponse(**profile)


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile_update: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    現在ログイン中のユーザーのプロフィール情報を更新

    認証が必要なエンドポイントです。

    Args:
        profile_update: 更新するプロフィール情報

    Returns:
        ProfileResponse: 更新後のプロフィール情報
    """
    user_id = current_user["id"]

    # profilesテーブルを更新
    response = (
        supabase.table("profiles")
        .update({"nickname": profile_update.nickname})
        .eq("id", user_id)
        .execute()
    )

    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プロフィールが見つかりません",
        )

    updated_profile = response.data[0]
    return ProfileResponse(**updated_profile)
