"""
旅行プラン関連のAPIエンドポイント
"""

import logging
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import httpx
from postgrest.exceptions import APIError
from supabase import Client
from uuid import UUID
from typing import List
from app.auth import get_current_user, ensure_rls
from app.database import get_supabase
from app.models.plan import (
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanCreate,
    PlanListResponse,
    PlanResponse,
)
from app.services.gemini_client import generate_travel_plan, generate_travel_plan_stream

router = APIRouter(prefix="/plans", tags=["Plans"], dependencies=[Depends(ensure_rls)])

logger = logging.getLogger(__name__)


def _enrich_waypoints_with_store_ids(plan: PlanGenerateResponse, supabase: Client):
    """
    生成されたプランのwaypointsに店舗IDを付与する

    店舗名や座標からstoresテーブルを検索し、マッチする店舗のIDを設定する

    Args:
        plan: 生成された旅行プラン
        supabase: Supabaseクライアント
    """
    if not plan.route or not plan.route.waypoints:
        return

    for waypoint in plan.route.waypoints:
        if waypoint.store_id:
            # 既にstore_idが設定されている場合はスキップ
            continue

        try:
            # 1. 店舗名での部分一致検索
            name_search = (
                supabase.table("stores")
                .select("id, name, latitude, longitude")
                .ilike("name", f"%{waypoint.name}%")
                .limit(10)
                .execute()
            )

            if name_search.data:
                # 名前が一致する店舗の中から、座標が最も近いものを選択
                closest_store = None
                min_distance = float('inf')

                for store in name_search.data:
                    # 簡易的な距離計算（緯度経度の差の二乗和）
                    lat_diff = waypoint.latitude - store["latitude"]
                    lng_diff = waypoint.longitude - store["longitude"]
                    distance = lat_diff ** 2 + lng_diff ** 2

                    if distance < min_distance:
                        min_distance = distance
                        closest_store = store

                # 距離が十分近い場合（約0.01度 = 約1km以内）のみマッチング
                if closest_store and min_distance < 0.01 ** 2:
                    waypoint.store_id = closest_store["id"]
                    logger.info(
                        f"Waypoint '{waypoint.name}' に店舗ID {closest_store['id']} "
                        f"({closest_store['name']}) を付与しました"
                    )
                    continue

            # 2. 座標での近接検索（名前でマッチしなかった場合）
            # 緯度経度で±0.001度（約100m）以内の店舗を検索
            coord_search = (
                supabase.table("stores")
                .select("id, name, latitude, longitude")
                .gte("latitude", waypoint.latitude - 0.001)
                .lte("latitude", waypoint.latitude + 0.001)
                .gte("longitude", waypoint.longitude - 0.001)
                .lte("longitude", waypoint.longitude + 0.001)
                .limit(10)
                .execute()
            )

            if coord_search.data:
                # 最も近い店舗を選択
                closest_store = None
                min_distance = float('inf')

                for store in coord_search.data:
                    lat_diff = waypoint.latitude - store["latitude"]
                    lng_diff = waypoint.longitude - store["longitude"]
                    distance = lat_diff ** 2 + lng_diff ** 2

                    if distance < min_distance:
                        min_distance = distance
                        closest_store = store

                if closest_store:
                    waypoint.store_id = closest_store["id"]
                    logger.info(
                        f"Waypoint '{waypoint.name}' に座標から店舗ID {closest_store['id']} "
                        f"({closest_store['name']}) を付与しました"
                    )

        except Exception as e:
            # エラーが発生してもプラン生成自体は失敗させない
            logger.warning(f"Waypoint '{waypoint.name}' への店舗ID付与に失敗: {e}")
            continue


@router.post("/generate", response_model=PlanGenerateResponse)
async def generate_plan(
    request: PlanGenerateRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    試合情報と現在地を基に、Gemini APIを使ってAI旅行プランを生成する

    認証が必要なエンドポイントです。

    Args:
        request: プラン生成リクエスト
        current_user: 認証済みユーザー情報
        supabase: Supabaseクライアント

    Returns:
        PlanGenerateResponse: 生成されたプラン情報

    Raises:
        HTTPException: 試合が見つからない場合（404）、プラン生成エラー（500）
    """
    # RLS適用はルーター依存関数 ensure_rls で共通化

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
    except (httpx.TimeoutException, httpx.HTTPError, APIError) as e:
        logger.warning(f"試合情報の取得でHTTP/Timeoutエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="試合情報の取得に失敗しました",
        )
    except Exception as e:
        logger.exception("試合情報の取得に失敗しました")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="試合情報の取得に失敗しました",
        )

    # Gemini APIを使って旅行プランを生成
    try:
        plan = generate_travel_plan(
            match_info=match,
            current_latitude=request.current_latitude,
            current_longitude=request.current_longitude,
            transport_mode=request.transport_mode.value,
        )

        # waypointsに店舗IDを付与（店舗名や座標からstoresテーブルを検索）
        _enrich_waypoints_with_store_ids(plan, supabase)

        logger.info(f"試合 {request.match_id} の旅行プラン生成に成功しました")
        return plan

    except ValueError as e:
        # GEMINI_API_KEYが設定されていない場合
        logger.error(f"Gemini API設定エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="旅行プラン生成サービスが利用できません。管理者に連絡してください。",
        )
    except Exception as e:
        logger.error(f"プラン生成エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="旅行プランの生成中にエラーが発生しました",
        )


@router.post("/generate/stream")
async def generate_plan_stream(
    request: PlanGenerateRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    試合情報と現在地を基に、Gemini APIを使ってAI旅行プランをストリーミング形式で生成する

    認証が必要なエンドポイントです。
    Server-Sent Events (SSE) 形式でストリーミングレスポンスを返します。

    Args:
        request: プラン生成リクエスト
        current_user: 認証済みユーザー情報
        supabase: Supabaseクライアント

    Returns:
        StreamingResponse: SSE形式のストリーミングレスポンス

    Raises:
        HTTPException: 試合が見つからない場合（404）、プラン生成エラー（500）
    """
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
    except (httpx.TimeoutException, httpx.HTTPError, APIError) as e:
        logger.warning(f"試合情報の取得でHTTP/Timeoutエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="試合情報の取得に失敗しました",
        )
    except Exception as e:
        logger.exception("試合情報の取得に失敗しました")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="試合情報の取得に失敗しました",
        )

    # ストリーミング生成関数
    async def event_generator():
        """Server-Sent Events形式でストリーミングデータを生成"""
        try:
            # Gemini APIからストリーミングで受信
            for chunk in generate_travel_plan_stream(
                match_info=match,
                current_latitude=request.current_latitude,
                current_longitude=request.current_longitude,
                transport_mode=request.transport_mode.value,
            ):
                # SSE形式: data: {chunk}\n\n
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # ストリーミング完了を通知
            yield f"data: {json.dumps({'done': True})}\n\n"

            logger.info(f"試合 {request.match_id} の旅行プランストリーミングが完了しました")

        except ValueError as e:
            # GEMINI_API_KEYが設定されていない場合
            logger.error(f"Gemini API設定エラー: {e}")
            error_msg = json.dumps({
                "error": "旅行プラン生成サービスが利用できません。管理者に連絡してください。"
            })
            yield f"data: {error_msg}\n\n"

        except Exception as e:
            logger.error(f"プラン生成ストリーミングエラー: {e}", exc_info=True)
            error_msg = json.dumps({
                "error": "旅行プランの生成中にエラーが発生しました"
            })
            yield f"data: {error_msg}\n\n"

    # StreamingResponseを返す
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginxでのバッファリング無効化
        },
    )


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
    logger.info(f"create_plan called: user_id={user_id}, match_id={plan.match_id}, title={plan.title}")

    # ユーザーのJWTトークンをSupabaseクライアントに適用してRLSを有効化
    from app.database import apply_user_jwt
    apply_user_jwt(supabase, current_user["access_token"])

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
    except (httpx.TimeoutException, httpx.HTTPError, APIError) as e:
        logger.warning(f"試合の存在確認でHTTP/Timeoutエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="試合の確認中にエラーが発生しました",
        )
    except Exception:
        logger.exception("試合の存在確認中にエラーが発生しました")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="試合の確認中にエラーが発生しました",
        )

    # プランを保存
    try:
        plan_data = {
            "user_id": user_id,
            "match_id": str(plan.match_id),
            "title": plan.title,
            "plan_details": plan.plan_details,
            "route_data": plan.route_data,
        }
        logger.info(f"Inserting plan data: {plan_data}")

        response = supabase.table("plans").insert(plan_data).execute()
        logger.info(f"Insert response: data={response.data}, error={getattr(response, 'error', None)}")

        if not response.data or len(response.data) == 0:
            logger.error(f"Insert returned empty data. Response: {response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="プランの保存に失敗しました",
            )

        saved_plan = response.data[0]
        logger.info(f"Plan saved successfully: {saved_plan}")
        return PlanResponse(**saved_plan)

    except HTTPException:
        raise
    except (httpx.TimeoutException, httpx.HTTPError, APIError) as e:
        logger.error(f"プラン保存でHTTP/Timeoutエラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プランの保存に失敗しました",
        )
    except Exception as e:
        logger.exception(f"プランの保存中にエラーが発生しました: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プランの保存に失敗しました",
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

    # ユーザーのJWTトークンをSupabaseクライアントに適用してRLSを有効化
    from app.database import apply_user_jwt
    apply_user_jwt(supabase, current_user["access_token"])

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

    except (httpx.TimeoutException, httpx.HTTPError, APIError) as e:
        logger.warning(f"プラン一覧取得でHTTP/Timeoutエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プラン一覧の取得に失敗しました",
        )
    except Exception:
        logger.exception("プラン一覧の取得に失敗しました")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プラン一覧の取得に失敗しました",
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

    # ユーザーのJWTトークンをSupabaseクライアントに適用してRLSを有効化
    from app.database import apply_user_jwt
    apply_user_jwt(supabase, current_user["access_token"])

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
    except (httpx.TimeoutException, httpx.HTTPError, APIError) as e:
        logger.warning(f"プラン取得でHTTP/Timeoutエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プランの取得に失敗しました",
        )
    except Exception:
        logger.exception("プランの取得に失敗しました")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プランの取得に失敗しました",
        )


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: UUID,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """
    保存したプランを削除する

    認証が必要なエンドポイントです。
    自分が保存したプランのみ削除可能です。

    Args:
        plan_id: プランID
        current_user: 認証済みユーザー情報
        supabase: Supabaseクライアント

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: プランが見つからない場合（404）、権限がない場合（403）
    """
    user_id = current_user["id"]

    # ユーザーのJWTトークンをSupabaseクライアントに適用してRLSを有効化
    from app.database import apply_user_jwt
    apply_user_jwt(supabase, current_user["access_token"])

    try:
        # プランの存在確認と権限チェック
        response = supabase.table("plans").select("id, user_id").eq("id", str(plan_id)).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたプランが見つかりません",
            )

        plan = response.data[0]

        # ユーザー自身のプランかチェック
        if plan["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="このプランを削除する権限がありません",
            )

        # プランを削除
        supabase.table("plans").delete().eq("id", str(plan_id)).execute()
        logger.info(f"プラン {plan_id} を削除しました (user_id: {user_id})")

    except HTTPException:
        raise
    except (httpx.TimeoutException, httpx.HTTPError, APIError) as e:
        logger.warning(f"プラン削除でHTTP/Timeoutエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プランの削除に失敗しました",
        )
    except Exception:
        logger.exception("プランの削除に失敗しました")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プランの削除に失敗しました",
        )
