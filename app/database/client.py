"""
Supabaseクライアントの設定と初期化
"""

import os
from supabase import create_client, Client
from functools import lru_cache


@lru_cache()
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


def get_supabase() -> Client:
    """
    FastAPIの依存性注入用のSupabaseクライアント取得関数

    Returns:
        Client: Supabaseクライアント
    """
    return get_supabase_client()
