"""
管理系のAPIエンドポイント

チェーン店名キャッシュの無効化・再取得など、運用向けの操作を提供する。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_user, ensure_rls
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

