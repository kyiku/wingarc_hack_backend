"""
店舗・レビュー関連のAPIエンドポイント

Currently provides a nearby local stores search using Google Places
with basic chain-store filtering.
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.auth import get_current_user
from app.database import get_supabase
from app.models.store import StoreSummary
from app.models.review import ReviewCreate, ReviewResponse
from app.services.google_places import search_nearby_local_stores


router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("/nearby", response_model=List[StoreSummary])
def get_nearby_stores(
    lat: float = Query(..., description="Center latitude", ge=-90.0, le=90.0),
    lng: float = Query(..., description="Center longitude", ge=-180.0, le=180.0),
    radius_m: int = Query(1000, description="Search radius in meters (<= 50000)", ge=1, le=50000),
    limit: int = Query(20, description="Max number of results", ge=1, le=50),
) -> List[StoreSummary]:
    """Search for nearby non-chain local stores.

    Notes:
        - Requires ``GOOGLE_PLACES_API_KEY`` to call live Google Places.
          If missing, returns deterministic stub results for development.
        - ``has_reviews`` and ``is_recommended`` are placeholders until DB is integrated.
    """

    try:
        stores = search_nearby_local_stores(
            latitude=lat, longitude=lng, radius_m=radius_m, max_results=limit
        )
        return stores
    except HTTPException:
        raise
    except Exception as exc:
        # Convert any unexpected error into a 500 with a concise message.
        raise HTTPException(status_code=500, detail=f"Failed to search nearby stores: {exc}")


@router.post("/{store_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    store_id: UUID,
    review: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    特定の店舗に新しい口コミを投稿する

    認証が必要なエンドポイントです。

    Args:
        store_id: 店舗ID
        review: レビュー情報（rating, comment）
        current_user: 認証済みユーザー情報
        supabase: Supabaseクライアント

    Returns:
        ReviewResponse: 投稿されたレビュー情報

    Raises:
        HTTPException: 店舗が見つからない場合（404）、データベースエラー（500）
    """
    user_id = current_user["id"]

    # 店舗の存在確認
    try:
        store_response = supabase.table("stores").select("id").eq("id", str(store_id)).execute()
        if not store_response.data or len(store_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された店舗が見つかりません",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"店舗の確認中にエラーが発生しました: {str(e)}",
        )

    # レビューをデータベースに保存
    try:
        review_data = {
            "store_id": str(store_id),
            "user_id": user_id,
            "rating": review.rating,
            "comment": review.comment,
        }

        response = supabase.table("reviews").insert(review_data).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="レビューの作成に失敗しました",
            )

        created_review = response.data[0]

        # ユーザーのニックネームを取得
        try:
            profile_response = supabase.table("profiles").select("nickname").eq("id", user_id).execute()
            user_name = (
                profile_response.data[0]["nickname"]
                if profile_response.data and len(profile_response.data) > 0
                else "匿名ユーザー"
            )
        except Exception:
            user_name = "匿名ユーザー"

        # レスポンスを構築
        return ReviewResponse(
            id=created_review["id"],
            store_id=created_review["store_id"],
            user_id=created_review["user_id"],
            user_name=user_name,
            rating=created_review["rating"],
            comment=created_review["comment"],
            created_at=created_review["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"レビューの投稿中にエラーが発生しました: {str(e)}",
        )
