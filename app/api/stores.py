"""
店舗・レビュー関連のAPIエンドポイント

Currently provides a nearby local stores search using Google Places
with basic chain-store filtering.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Set
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

        # DBに存在するものについて has_reviews / is_recommended を付与
        try:
            # Supabaseクライアント（未設定時はそのまま返す）
            from app.services.supabase_client import get_client as _get_client

            client = _get_client()
            if client is None or not stores:
                return stores

            gpids = [s.google_place_id for s in stores]
            # storesテーブルで対応するレコードを一括取得
            resp = client.table("stores").select("id,google_place_id").in_("google_place_id", gpids).execute()
            rows = getattr(resp, "data", None) or []
            gpid_to_id: Dict[str, str] = {}
            store_ids: List[str] = []
            for r in rows:
                sid = r.get("id")
                gpid = r.get("google_place_id")
                if sid and gpid:
                    gpid_to_id[str(gpid)] = str(sid)
                    store_ids.append(str(sid))

            if not store_ids:
                return stores

            # reviews / player_recommendations の存在チェックを一括で
            has_review_ids: Set[str] = set()
            try:
                rresp = (
                    client.table("reviews").select("store_id").in_("store_id", store_ids).execute()
                )
                for rr in getattr(rresp, "data", None) or []:
                    sid = rr.get("store_id")
                    if sid:
                        has_review_ids.add(str(sid))
            except Exception:
                has_review_ids = set()

            rec_ids: Set[str] = set()
            try:
                presp = (
                    client.table("player_recommendations").select("store_id").in_("store_id", store_ids).execute()
                )
                for pr in getattr(presp, "data", None) or []:
                    sid = pr.get("store_id")
                    if sid:
                        rec_ids.add(str(sid))
            except Exception:
                rec_ids = set()

            # アノテーション
            for s in stores:
                sid = gpid_to_id.get(s.google_place_id)
                if sid:
                    s.id = sid
                    s.has_reviews = sid in has_review_ids
                    s.is_recommended = sid in rec_ids

            return stores
        except Exception:
            # DB連携で問題があっても検索結果自体は返す
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
    """特定店舗の詳細情報を返す。

    含まれる情報:
        - stores: 基本情報（住所・座標・開店時間など）
        - reviews: 口コミ一覧（ユーザー名は profiles.nickname より解決）
        - player_recommendations: 選手のおすすめ一覧

    認証は不要。
    """

    # 1) 店舗の基本情報
    try:
        store_resp = supabase.table("stores").select("*").eq("id", str(store_id)).execute()
        if not store_resp.data:
            raise HTTPException(status_code=404, detail="指定された店舗が見つかりません")
        store = store_resp.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"店舗情報の取得に失敗しました: {exc}")

    # 開店時間はDB側でjsonb。配列の文字列に丸める（可能なら）
    opening_hours_raw: Optional[object] = store.get("opening_hours")
    opening_hours: Optional[List[str]] = None
    try:
        if isinstance(opening_hours_raw, list):
            # 文字列配列であればそのまま、辞書配列なら代表的な文字列を抽出
            if all(isinstance(x, str) for x in opening_hours_raw):
                opening_hours = opening_hours_raw  # type: ignore[assignment]
            elif all(isinstance(x, dict) for x in opening_hours_raw):
                # Google Placesのweekday_textのようなフィールドがあれば使う
                candidate = []
                for item in opening_hours_raw:  # type: ignore[assignment]
                    text = item.get("weekday_text") or item.get("text")
                    if isinstance(text, str):
                        candidate.append(text)
                opening_hours = candidate or None
        elif isinstance(opening_hours_raw, dict):
            # { weekday_text: [...] } 形式を想定
            wt = opening_hours_raw.get("weekday_text")
            if isinstance(wt, list) and all(isinstance(x, str) for x in wt):
                opening_hours = wt  # type: ignore[assignment]
    except Exception:
        opening_hours = None

    # 2) レビュー一覧の取得（ユーザー名解決を含む）
    reviews: List[ReviewResponse] = []
    try:
        rev_resp = (
            supabase.table("reviews")
            .select("id, store_id, user_id, rating, comment, created_at")
            .eq("store_id", str(store_id))
            .order("created_at", desc=True)
            .execute()
        )

        for row in rev_resp.data or []:
            user_id = row.get("user_id")
            user_name = "匿名ユーザー"
            try:
                prof_resp = (
                    supabase.table("profiles").select("nickname").eq("id", user_id).execute()
                )
                if prof_resp.data and len(prof_resp.data) > 0:
                    nickname = prof_resp.data[0].get("nickname")
                    if isinstance(nickname, str) and nickname:
                        user_name = nickname
            except Exception:
                user_name = "匿名ユーザー"

            try:
                reviews.append(
                    ReviewResponse(
                        id=row.get("id"),
                        store_id=row.get("store_id"),
                        user_id=row.get("user_id"),
                        user_name=user_name,
                        rating=row.get("rating"),
                        comment=row.get("comment"),
                        created_at=row.get("created_at"),
                    )
                )
            except Exception:
                # 型不一致などでスキップ
                continue
    except Exception as exc:
        # レビューは取得失敗しても全体を落とさず、空配列で返す
        reviews = []

    # 3) 選手おすすめの取得
    recommendations: List[PlayerRecommendation] = []
    try:
        rec_resp = (
            supabase.table("player_recommendations")
            .select("id, player_name, comment, created_at")
            .eq("store_id", str(store_id))
            .order("created_at", desc=True)
            .execute()
        )
        for row in rec_resp.data or []:
            try:
                recommendations.append(
                    PlayerRecommendation(
                        id=str(row.get("id")),
                        player_name=str(row.get("player_name")),
                        comment=str(row.get("comment")),
                    )
                )
            except Exception:
                continue
    except Exception:
        recommendations = []

    # 4) まとめて返す
    return StoreDetail(
        id=str(store.get("id")),
        google_place_id=str(store.get("google_place_id")),
        name=str(store.get("name")),
        address=str(store.get("address") or ""),
        latitude=float(store.get("latitude")),
        longitude=float(store.get("longitude")),
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
    # PostgREST にエンドユーザーのJWTを付与（RLSのINSERT/SELECT適用のため）
    try:
        postgrest = getattr(supabase, "postgrest", None)
        if postgrest and hasattr(postgrest, "auth"):
            postgrest.auth(current_user.get("access_token", ""))
    except Exception:
        pass

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
