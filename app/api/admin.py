"""
管理系のAPIエンドポイント

チェーン店名キャッシュの無効化・再取得や、試合情報の登録・更新・削除など
運用向けの操作を提供する。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client

from app.auth import get_current_user, ensure_rls
from app.database import get_supabase
from app.models.match import MatchResponse
from app.services.chain_filter import (
    invalidate_dynamic_chain_keywords_cache,
    refresh_dynamic_chain_keywords,
)


router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(ensure_rls)])


def _is_admin(user: Dict[str, Any]) -> bool:
    meta = user.get("user_metadata") or {}
    if isinstance(meta, dict) and meta.get("is_admin") is True:
        return True
    allow = os.getenv("ADMIN_EMAILS", "")
    if allow:
        allow_list = {e.strip().lower() for e in allow.split(",") if e.strip()}
        email = str(user.get("email") or "").lower()
        if email and email in allow_list:
            return True
    return False


@router.post("/cache/chain_keywords/invalidate")
async def invalidate_chain_keywords_cache(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """チェーン店名のTTLキャッシュを即時クリアする（管理者限定）。"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理者権限が必要です")
    invalidate_dynamic_chain_keywords_cache()
    return {"status": "ok", "action": "invalidate"}


@router.post("/cache/chain_keywords/refresh")
async def refresh_chain_keywords_cache(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """DBから再取得してキャッシュを更新（管理者限定）。"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理者権限が必要です")
    names: List[str] = refresh_dynamic_chain_keywords()
    return {"status": "ok", "action": "refresh", "count": len(names)}


# ============================
# 試合情報 管理API (CRUDの一部)
# ============================


class MatchUpsert(BaseModel):
    """試合情報の作成/全体更新用モデル。

    Note:
        - `match_datetime` はISO 8601の日時（タイムゾーン付き）を想定。
        - 文字列項目は空文字不可。
    """

    match_datetime: datetime = Field(description="キックオフ日時（ISO 8601）")
    opponent: str = Field(min_length=1, description="対戦相手")
    venue_name: str = Field(min_length=1, description="会場名")
    venue_latitude: float = Field(description="会場の緯度")
    venue_longitude: float = Field(description="会場の経度")


class MatchPartialUpdate(BaseModel):
    """試合情報の部分更新用モデル（PATCH）。"""

    match_datetime: Optional[datetime] = Field(default=None, description="キックオフ日時")
    opponent: Optional[str] = Field(default=None, min_length=1, description="対戦相手")
    venue_name: Optional[str] = Field(default=None, min_length=1, description="会場名")
    venue_latitude: Optional[float] = Field(default=None, description="会場の緯度")
    venue_longitude: Optional[float] = Field(default=None, description="会場の経度")


def _require_admin(user: Dict[str, Any]) -> None:
    if not _is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理者権限が必要です")


@router.post("/matches", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_match(
    payload: MatchUpsert,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """試合情報を新規登録（管理者限定）。"""
    _require_admin(current_user)

    data = {
        "match_datetime": payload.match_datetime.isoformat(),
        "opponent": payload.opponent,
        "venue_name": payload.venue_name,
        "venue_latitude": payload.venue_latitude,
        "venue_longitude": payload.venue_longitude,
    }

    try:
        resp = (
            supabase.table("matches")
            .insert(data)
            .select("id, match_datetime, opponent, venue_name, venue_latitude, venue_longitude")
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=500, detail="試合情報の登録に失敗しました")
        return MatchResponse.model_validate(rows[0])
    except HTTPException:
        raise
    except Exception:
        # 具体的なエラーは内部ログへ。クライアントには汎用メッセージ。
        raise HTTPException(status_code=500, detail="試合情報の登録に失敗しました")


@router.put("/matches/{match_id}", response_model=MatchResponse)
async def admin_update_match(
    match_id: UUID,
    payload: MatchUpsert,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """試合情報を全体更新（管理者限定）。存在しない場合は404。"""
    _require_admin(current_user)

    # 存在確認
    try:
        exist = supabase.table("matches").select("id").eq("id", str(match_id)).single().execute()
        if not getattr(exist, "data", None):
            raise HTTPException(status_code=404, detail="指定された試合が見つかりません")
    except HTTPException:
        raise
    except Exception:
        # 存在確認に失敗
        raise HTTPException(status_code=500, detail="試合情報の更新に失敗しました")

    data = {
        "match_datetime": payload.match_datetime.isoformat(),
        "opponent": payload.opponent,
        "venue_name": payload.venue_name,
        "venue_latitude": payload.venue_latitude,
        "venue_longitude": payload.venue_longitude,
    }

    try:
        resp = (
            supabase.table("matches")
            .update(data)
            .eq("id", str(match_id))
            .select("id, match_datetime, opponent, venue_name, venue_latitude, venue_longitude")
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            # RLSにより更新できなかった等
            raise HTTPException(status_code=404, detail="指定された試合が見つかりません")
        return MatchResponse.model_validate(rows[0])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="試合情報の更新に失敗しました")


@router.patch("/matches/{match_id}", response_model=MatchResponse)
async def admin_patch_match(
    match_id: UUID,
    payload: MatchPartialUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """試合情報の部分更新（管理者限定）。"""
    _require_admin(current_user)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="更新内容が指定されていません")
    if "match_datetime" in update_data and isinstance(update_data["match_datetime"], datetime):
        update_data["match_datetime"] = update_data["match_datetime"].isoformat()

    # 存在確認
    try:
        exist = supabase.table("matches").select("id").eq("id", str(match_id)).single().execute()
        if not getattr(exist, "data", None):
            raise HTTPException(status_code=404, detail="指定された試合が見つかりません")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="試合情報の更新に失敗しました")

    try:
        resp = (
            supabase.table("matches")
            .update(update_data)
            .eq("id", str(match_id))
            .select("id, match_datetime, opponent, venue_name, venue_latitude, venue_longitude")
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="指定された試合が見つかりません")
        return MatchResponse.model_validate(rows[0])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="試合情報の更新に失敗しました")


@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_match(
    match_id: UUID,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """試合情報を削除（管理者限定）。存在しない場合は404。"""
    _require_admin(current_user)

    # 存在確認
    try:
        exist = supabase.table("matches").select("id").eq("id", str(match_id)).single().execute()
        if not getattr(exist, "data", None):
            raise HTTPException(status_code=404, detail="指定された試合が見つかりません")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="試合情報の削除に失敗しました")

    try:
        supabase.table("matches").delete().eq("id", str(match_id)).execute()
        return None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="試合情報の削除に失敗しました")

