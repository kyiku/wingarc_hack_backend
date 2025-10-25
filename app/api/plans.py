"""
旅行プラン関連のAPIエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from uuid import UUID
from typing import List
from app.auth import get_current_user
from app.database import get_supabase
from app.models.plan import (
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanCreate,
    PlanListResponse,
    PlanResponse,
    Waypoint,
    RouteStep,
    Route,
)

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.post("/generate", response_model=PlanGenerateResponse)
async def generate_plan(
    request: PlanGenerateRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    試合情報と現在地を基に、AI旅行プランを生成する

    認証が必要なエンドポイントです。
    ※ 現在はダミーデータを返却します。Gemini API連携は今後実装予定。

    Args:
        request: プラン生成リクエスト
        current_user: 認証済みユーザー情報
        supabase: Supabaseクライアント

    Returns:
        PlanGenerateResponse: 生成されたプラン情報

    Raises:
        HTTPException: 試合が見つからない場合（404）
    """
    # PostgREST にエンドユーザーのJWTを付与（RLS前提のクエリ用）
    try:
        postgrest = getattr(supabase, "postgrest", None)
        if postgrest and hasattr(postgrest, "auth"):
            postgrest.auth(current_user.get("access_token", ""))
    except Exception:
        pass

    # 試合の存在確認
    try:
        match_response = (
            supabase.table("matches")
            .select("*")
            .eq("id", str(request.match_id))
            .execute()
        )

        if not match_response.data or len(match_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された試合が見つかりません",
            )

        match = match_response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"試合情報の取得中にエラーが発生しました: {str(e)}",
        )

    # TODO: 実際にはGemini APIを呼び出してプランを生成
    # 現在はダミーデータを返却
    dummy_plan = PlanGenerateResponse(
        plan_text=(
            f"試合観戦お疲れ様！{match['opponent']}戦の観戦プランをご提案します。\n\n"
            f"まずは現在地から{request.transport_mode}で移動して、スタジアム近くのカフェで一息つきましょう。\n"
            f"試合開始の1時間前には{match['venue_name']}に到着することをおすすめします。\n"
            f"試合後は地元の名店で食事を楽しみましょう！"
        ),
        route=Route(
            waypoints=[
                Waypoint(
                    name="現在地",
                    latitude=request.current_latitude,
                    longitude=request.current_longitude,
                    store_id=None,
                ),
                Waypoint(
                    name=match["venue_name"],
                    latitude=match["venue_latitude"],
                    longitude=match["venue_longitude"],
                    store_id=None,
                ),
            ],
            total_duration_minutes=30,
            steps=[
                RouteStep(
                    from_="現在地",
                    to=match["venue_name"],
                    transport=request.transport_mode,
                    duration_minutes=30,
                )
            ],
        ),
    )

    return dummy_plan


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan: PlanCreate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    生成された旅行プランをデータベースに保存する

    認証が必要なエンドポイントです。

    Args:
        plan: プラン情報
        current_user: 認証済みユーザー情報
        supabase: Supabaseクライアント

    Returns:
        PlanResponse: 保存されたプラン情報

    Raises:
        HTTPException: 試合が見つからない場合（404）、データベースエラー（500）
    """
    user_id = current_user["id"]
    # PostgREST にエンドユーザーのJWTを付与（RLSのINSERT適用のため）
    try:
        postgrest = getattr(supabase, "postgrest", None)
        if postgrest and hasattr(postgrest, "auth"):
            postgrest.auth(current_user.get("access_token", ""))
    except Exception:
        pass

    # 試合の存在確認
    try:
        match_response = supabase.table("matches").select("id").eq("id", str(plan.match_id)).execute()
        if not match_response.data or len(match_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された試合が見つかりません",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"試合の確認中にエラーが発生しました: {str(e)}",
        )

    # プランを保存
    try:
        plan_data = {
            "user_id": user_id,
            "match_id": str(plan.match_id),
            "title": plan.title,
            "plan_details": plan.plan_details,
        }

        response = supabase.table("plans").insert(plan_data).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="プランの保存に失敗しました",
            )

        saved_plan = response.data[0]
        return PlanResponse(**saved_plan)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プランの保存中にエラーが発生しました: {str(e)}",
        )


@router.get("", response_model=List[PlanListResponse])
async def get_plans(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    ログイン中のユーザーが保存したプランの一覧を取得する

    認証が必要なエンドポイントです。

    Args:
        current_user: 認証済みユーザー情報
        supabase: Supabaseクライアント

    Returns:
        List[PlanListResponse]: プラン一覧

    Raises:
        HTTPException: データベースエラー（500）
    """
    user_id = current_user["id"]
    # PostgREST にエンドユーザーのJWTを付与（RLSのSELECT適用のため）
    try:
        postgrest = getattr(supabase, "postgrest", None)
        if postgrest and hasattr(postgrest, "auth"):
            postgrest.auth(current_user.get("access_token", ""))
    except Exception:
        pass

    try:
        response = (
            supabase.table("plans")
            .select("id, match_id, title, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        plans = [PlanListResponse(**plan) for plan in response.data]
        return plans

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プラン一覧の取得中にエラーが発生しました: {str(e)}",
        )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: UUID,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    保存したプランの詳細情報を取得する

    認証が必要なエンドポイントです。
    自分が保存したプランのみ取得可能です。

    Args:
        plan_id: プランID
        current_user: 認証済みユーザー情報
        supabase: Supabaseクライアント

    Returns:
        PlanResponse: プラン詳細情報

    Raises:
        HTTPException: プランが見つからない場合（404）、権限がない場合（403）
    """
    user_id = current_user["id"]
    # PostgREST にエンドユーザーのJWTを付与（RLSのSELECT適用のため）
    try:
        postgrest = getattr(supabase, "postgrest", None)
        if postgrest and hasattr(postgrest, "auth"):
            postgrest.auth(current_user.get("access_token", ""))
    except Exception:
        pass

    try:
        response = supabase.table("plans").select("*").eq("id", str(plan_id)).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたプランが見つかりません",
            )

        plan = response.data[0]

        # ユーザー自身のプランかチェック（RLSでも制御されているが、明示的にチェック）
        if plan["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="このプランにアクセスする権限がありません",
            )

        return PlanResponse(**plan)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プランの取得中にエラーが発生しました: {str(e)}",
        )
