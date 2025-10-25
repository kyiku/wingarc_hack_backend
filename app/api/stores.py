"""
店舗・レビュー関連のAPIエンドポイント

Currently provides a nearby local stores search using Google Places
with basic chain-store filtering.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.auth import get_current_user
from app.database import get_supabase
from app.models.store import StoreSummary, StoreDetail, PlayerRecommendation
from app.models.review import ReviewCreate, ReviewResponse
from app.services.google_places import search_nearby_local_stores


router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("/nearby", response_model=List[StoreSummary])
async def get_nearby_stores(
    lat: float = Query(..., description="Center latitude", ge=-90.0, le=90.0),
    lng: float = Query(..., description="Center longitude", ge=-180.0, le=180.0),
    radius_m: int = Query(1000, description="Search radius in meters (<= 50000)", ge=1, le=50000),
    limit: int = Query(20, description="Max number of results", ge=1, le=50),
    supabase: Client = Depends(get_supabase),
) -> List[StoreSummary]:
    """Search for nearby non-chain local stores.

    Notes:
        - Requires ``GOOGLE_PLACES_API_KEY`` to call live Google Places.
          If missing, returns deterministic stub results for development.
        - ``has_reviews`` and ``is_recommended`` flags are set based on DB data.
    """

    try:
        stores = search_nearby_local_stores(
            latitude=lat, longitude=lng, radius_m=radius_m, max_results=limit
        )

        if not stores:
            return []

        # Google Place IDsを収集
        google_place_ids = [store.google_place_id for store in stores]

        # storesテーブルから該当する店舗を一括取得
        try:
            stores_response = (
                supabase.table("stores")
                .select("id, google_place_id")
                .in_("google_place_id", google_place_ids)
                .execute()
            )

            # google_place_id -> store_id のマッピングを作成
            place_id_to_store_id = {}
            store_ids = []
            for db_store in stores_response.data or []:
                place_id = db_store.get("google_place_id")
                store_id = db_store.get("id")
                if place_id and store_id:
                    place_id_to_store_id[place_id] = store_id
                    store_ids.append(str(store_id))

            # has_reviewsとis_recommendedフラグを設定
            has_reviews_set = set()
            is_recommended_set = set()

            if store_ids:
                # reviewsテーブルをチェック
                try:
                    reviews_response = (
                        supabase.table("reviews").select("store_id").in_("store_id", store_ids).execute()
                    )
                    for review in reviews_response.data or []:
                        store_id = review.get("store_id")
                        if store_id:
                            has_reviews_set.add(str(store_id))
                except Exception:
                    pass

                # player_recommendationsテーブルをチェック
                try:
                    recs_response = (
                        supabase.table("player_recommendations")
                        .select("store_id")
                        .in_("store_id", store_ids)
                        .execute()
                    )
                    for rec in recs_response.data or []:
                        store_id = rec.get("store_id")
                        if store_id:
                            is_recommended_set.add(str(store_id))
                except Exception:
                    pass

            # 各店舗にフラグを設定
            for store in stores:
                store_id = place_id_to_store_id.get(store.google_place_id)
                if store_id:
                    store.id = store_id
                    store.has_reviews = store_id in has_reviews_set
                    store.is_recommended = store_id in is_recommended_set

        except Exception:
            # DB連携に失敗してもGoogle Places APIの結果は返す
            pass

        return stores
    except HTTPException:
        raise
    except Exception as exc:
        # Convert any unexpected error into a 500 with a concise message.
        raise HTTPException(status_code=500, detail=f"Failed to search nearby stores: {exc}")


@router.get("/{store_id}", response_model=StoreDetail)
async def get_store_detail(
    store_id: UUID,
    supabase: Client = Depends(get_supabase),
):
    """
    特定の店舗の詳細情報を取得する

    店舗の基本情報、口コミ、選手のおすすめ情報を含みます。

    Args:
        store_id: 店舗ID
        supabase: Supabaseクライアント

    Returns:
        StoreDetail: 店舗詳細情報

    Raises:
        HTTPException: 店舗が見つからない場合（404）、データベースエラー（500）
    """
    # 店舗情報を取得
    try:
        store_response = supabase.table("stores").select("*").eq("id", str(store_id)).execute()
        if not store_response.data or len(store_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された店舗が見つかりません",
            )
        store = store_response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"店舗情報の取得中にエラーが発生しました: {str(e)}",
        )

    # opening_hoursをパース
    opening_hours: Optional[List[str]] = None
    if store.get("opening_hours"):
        opening_hours_raw = store["opening_hours"]
        if isinstance(opening_hours_raw, list):
            opening_hours = opening_hours_raw
        elif isinstance(opening_hours_raw, dict):
            # Google Places APIの形式を想定
            weekday_text = opening_hours_raw.get("weekday_text")
            if isinstance(weekday_text, list):
                opening_hours = weekday_text

    # レビューを取得（profilesと結合してuser_nameを取得）
    reviews: List[ReviewResponse] = []
    try:
        reviews_response = (
            supabase.table("reviews")
            .select("*")
            .eq("store_id", str(store_id))
            .order("created_at", desc=True)
            .execute()
        )

        # 各レビューのuser_idからニックネームを取得
        for review_data in reviews_response.data or []:
            user_id = review_data.get("user_id")
            user_name = "匿名ユーザー"

            if user_id:
                try:
                    profile_response = (
                        supabase.table("profiles").select("nickname").eq("id", user_id).execute()
                    )
                    if profile_response.data and len(profile_response.data) > 0:
                        user_name = profile_response.data[0].get("nickname", "匿名ユーザー")
                except Exception:
                    pass

            reviews.append(
                ReviewResponse(
                    id=review_data["id"],
                    store_id=review_data["store_id"],
                    user_id=review_data["user_id"],
                    user_name=user_name,
                    rating=review_data["rating"],
                    comment=review_data.get("comment", ""),
                    created_at=review_data["created_at"],
                )
            )
    except Exception:
        # レビュー取得失敗時は空配列
        reviews = []

    # 選手のおすすめ情報を取得
    recommendations: List[PlayerRecommendation] = []
    try:
        rec_response = (
            supabase.table("player_recommendations")
            .select("*")
            .eq("store_id", str(store_id))
            .order("created_at", desc=True)
            .execute()
        )

        for rec_data in rec_response.data or []:
            recommendations.append(
                PlayerRecommendation(
                    id=str(rec_data["id"]),
                    player_name=rec_data["player_name"],
                    comment=rec_data.get("comment", ""),
                )
            )
    except Exception:
        # 選手おすすめ取得失敗時は空配列
        recommendations = []

    # レスポンスを構築
    return StoreDetail(
        id=str(store["id"]),
        google_place_id=store["google_place_id"],
        name=store["name"],
        address=store.get("address", ""),
        latitude=float(store["latitude"]),
        longitude=float(store["longitude"]),
        opening_hours=opening_hours,
        reviews=reviews,
        recommendations=recommendations,
    )


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
