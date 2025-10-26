"""
ユーザー関連のAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import List
from supabase import Client
from app.auth import get_current_user, ensure_rls
from app.database import get_supabase
from app.models.user import ProfileResponse, ProfileUpdate
from app.models.review import ReviewResponse

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(ensure_rls)])

logger = logging.getLogger(__name__)


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
    # 1) まずはDB側の結合RPCを優先（auth.users × profiles）
    try:
        rpc_resp = supabase.rpc("get_me_profile").execute()
        data = getattr(rpc_resp, "data", None)
        if data:
            row = data[0] if isinstance(data, list) else data
            return ProfileResponse(
                id=row.get("id"),
                email=row.get("email") or "",
                nickname=row.get("nickname") or "",
            )
    except Exception:
        # RPCの利用不可（未定義・権限）などはフォールバック
        logger.debug("get_me_profile RPCの呼び出しに失敗。profiles直参照へフォールバック")
        pass

    # 2) フォールバック: profiles から取得し、email はAuth情報から合成
    response = supabase.table("profiles").select("*").eq("id", user_id).execute()

    # プロフィールが存在しない場合は自動作成
    if not response.data or len(response.data) == 0:
        logger.info(f"プロフィールが存在しないため、ユーザーID {user_id} の新規プロフィールを作成します")
        # user_metadataからnicknameを取得
        nickname = str(current_user.get("user_metadata", {}).get("nickname", ""))

        # 新規プロフィールを作成
        insert_response = supabase.table("profiles").insert({
            "id": user_id,
            "nickname": nickname
        }).execute()

        if not insert_response.data or len(insert_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="プロフィールの作成に失敗しました",
            )

        profile = insert_response.data[0]
    else:
        profile = response.data[0]

    email = str(current_user.get("email") or "")
    return ProfileResponse(id=profile["id"], nickname=profile["nickname"], email=email)


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

    # 1) まずは結合RPCで更新＋取得
    try:
        rpc_resp = supabase.rpc(
            "update_my_nickname", {"new_nickname": profile_update.nickname}
        ).execute()
        data = getattr(rpc_resp, "data", None)
        if data:
            row = data[0] if isinstance(data, list) else data
            return ProfileResponse(
                id=row.get("id"),
                email=row.get("email") or "",
                nickname=row.get("nickname") or "",
            )
    except Exception:
        # RPCの利用不可（未定義・権限）などはフォールバック
        logger.debug("update_my_nickname RPCの呼び出しに失敗。profiles直接更新へフォールバック")
        pass

    # 2) フォールバック: profilesを直接更新して合成
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
    email = str(current_user.get("email") or "")
    return ProfileResponse(id=updated_profile["id"], nickname=updated_profile["nickname"], email=email)


@router.get("/me/reviews", response_model=List[ReviewResponse])
async def get_my_reviews(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    現在ログイン中のユーザーが投稿した口コミを取得

    認証が必要なエンドポイントです。

    Returns:
        List[ReviewResponse]: ユーザーが投稿した口コミのリスト
    """
    user_id = current_user["id"]

    try:
        # reviewsテーブルから、ユーザーが投稿した口コミを取得
        # profilesテーブルと結合してニックネームも取得
        response = (
            supabase.table("reviews")
            .select("*, profiles(nickname)")
            .eq("user_id", user_id)
            .order("created_at", {"ascending": False})
            .execute()
        )

        reviews = []
        for row in response.data:
            # profilesがネストされているので展開
            nickname = row.get("profiles", {}).get("nickname", "") if row.get("profiles") else ""

            reviews.append(ReviewResponse(
                id=row["id"],
                store_id=row["store_id"],
                user_id=row["user_id"],
                username=nickname,
                rating=row["rating"],
                comment=row["comment"],
                created_at=row["created_at"],
            ))

        return reviews

    except Exception as e:
        logger.exception("ユーザーの口コミ取得中にエラーが発生しました")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="口コミの取得に失敗しました",
        )
