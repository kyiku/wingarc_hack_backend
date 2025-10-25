"""
Supabaseクライアントの設定と初期化

方針:
- 原則としてリクエストスコープのクライアント（request.state.supabase）を使用。
- 上記がない場合のみ新しいクライアントを生成して返す（グローバルなシングルトンは保持しない）。
  RLSのJWT適用は状態を持つため、共有インスタンスの使い回しは避ける。
"""

import os
from typing import Optional
from fastapi import Request
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """
    Supabaseクライアントのシングルトンインスタンスを取得

    Returns:
        Client: Supabaseクライアント

    Raises:
        ValueError: 環境変数が設定されていない場合
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url:
        raise ValueError("SUPABASE_URLが設定されていません")
    if not supabase_key:
        raise ValueError("SUPABASE_KEYが設定されていません")

    return create_client(supabase_url, supabase_key)


def get_supabase(request: Optional[Request] = None) -> Client:
    """
    FastAPIの依存性注入用のSupabaseクライアント取得関数

    Returns:
        Client: Supabaseクライアント
    """
    # ルーター／ミドルウェアで request.state.supabase がセットされていればそれを優先
    if request is not None:
        sb = getattr(request.state, "supabase", None)
        if sb is not None:
            return sb
    return get_supabase_client()


def apply_user_jwt(supabase: Client, token: str) -> None:
    """PostgREST にユーザーのJWTを適用するヘルパー関数。

    Args:
        supabase: Supabaseクライアント
        token: エンドユーザーのアクセストークン（Bearerの中身）

    Note:
        - PostgRESTの`auth`が利用できない環境や例外発生時は何もせず安全に無視する。
        - 現在は副作用のある操作のため、必要な箇所で都度呼び出すこと。
    """
    try:
        postgrest = getattr(supabase, "postgrest", None)
        if postgrest and hasattr(postgrest, "auth"):
            postgrest.auth(token or "")
    except Exception:
        # フェイルソフト: JWT適用に失敗しても処理は継続する
        pass
