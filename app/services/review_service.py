"""
Review-related helpers

店舗詳細で用いるレビュー一覧取得をサービス層に切り出し、
エンドポイントの複雑なパース処理を排除する。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import httpx
from postgrest.exceptions import APIError

from app.models.review import ReviewResponse


logger = logging.getLogger(__name__)


def _extract_nickname(profile: Any) -> Optional[str]:
    """PostgRESTの埋め込み結果 `profiles` からニックネームを抽出。

    埋め込みの形状は dict または list[dict] の可能性がある。
    取得できない場合は None。
    """
    try:
        if isinstance(profile, dict):
            nick = profile.get("nickname")
            return nick if isinstance(nick, str) and nick else None
        if isinstance(profile, list) and profile:
            first = profile[0]
            if isinstance(first, dict):
                nick = first.get("nickname")
                return nick if isinstance(nick, str) and nick else None
        return None
    except Exception:
        return None


def list_reviews_with_usernames(
    *, supabase, store_id: str, limit: int = 50
) -> List[ReviewResponse]:
    """レビューをユーザー名付きで取得する（埋め込み→IN句フォールバック）。

    Args:
        supabase: Supabase Client
        store_id: 対象店舗ID（UUIDの文字列）
        limit: 取得件数の上限
    """

    # 1) 埋め込みで1クエリ化を試みる
    try:
        rev_resp = (
            supabase.table("reviews")
            .select(
                "id, store_id, user_id, rating, comment, created_at, profiles(nickname)"
            )
            .eq("store_id", store_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = getattr(rev_resp, "data", None) or []
        results: List[ReviewResponse] = []
        for row in rows:
            profile = row.get("profiles")
            nickname = _extract_nickname(profile)
            user_name = nickname if isinstance(nickname, str) and nickname else "匿名ユーザー"
            try:
                results.append(
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
                # 型不一致等はスキップ
                continue
        return results
    except (httpx.TimeoutException, httpx.HTTPError, APIError):
        # フォールバックへ
        logger.warning("レビュー埋め込み取得に失敗。IN句フォールバックを実行")
    except Exception:
        # 予期しない異常はフォールバックしつつログ
        logger.exception("レビュー埋め込み取得で予期しないエラー")

    # 2) フォールバック: reviews → profiles を IN 句で一括解決
    rev_resp = (
        supabase.table("reviews")
        .select("id, store_id, user_id, rating, comment, created_at")
        .eq("store_id", store_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = getattr(rev_resp, "data", None) or []

    user_ids = [str(r.get("user_id")) for r in rows if r.get("user_id")]
    unique_user_ids = sorted(set(user_ids))

    nickname_map: Dict[str, str] = {}
    if unique_user_ids:
        try:
            prof_resp = (
                supabase.table("profiles").select("id, nickname").in_("id", unique_user_ids).execute()
            )
            for pr in getattr(prof_resp, "data", None) or []:
                uid = pr.get("id")
                nk = pr.get("nickname")
                if uid and isinstance(uid, str) and isinstance(nk, str) and nk:
                    nickname_map[uid] = nk
        except (httpx.TimeoutException, httpx.HTTPError, APIError):
            nickname_map = {}
        except Exception:
            nickname_map = {}

    results: List[ReviewResponse] = []
    for row in rows:
        try:
            uid = row.get("user_id")
            user_name = nickname_map.get(str(uid), "匿名ユーザー")
            results.append(
                ReviewResponse(
                    id=row.get("id"),
                    store_id=row.get("store_id"),
                    user_id=uid,
                    user_name=user_name,
                    rating=row.get("rating"),
                    comment=row.get("comment"),
                    created_at=row.get("created_at"),
                )
            )
        except Exception:
            continue
    return results

