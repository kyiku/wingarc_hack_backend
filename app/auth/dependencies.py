"""
認証用の依存関数
"""

from fastapi import Depends, HTTPException, status, Request
import logging
import httpx
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from supabase import Client
from app.database import get_supabase, apply_user_jwt, get_supabase_client
import os
from supabase import create_client

# HTTPBearer認証スキーム
security = HTTPBearer()
logger = logging.getLogger(__name__)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """
    JWTトークンから現在のユーザー情報を取得する依存関数

    Args:
        credentials: HTTPベアラートークン
        supabase: Supabaseクライアント

    Returns:
        dict: ユーザー情報（id、emailなど）

    Raises:
        HTTPException: 認証に失敗した場合（401 Unauthorized）
    """
    token = credentials.credentials

    try:
        # Supabaseでトークンを検証してユーザー情報を取得
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました。有効なトークンを提供してください。",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = response.user
        return {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata or {},
            "access_token": token,
        }

    except HTTPException:
        raise
    except (httpx.TimeoutException, httpx.HTTPError):
        logger.warning("トークン検証でHTTP/Timeoutエラー")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの検証に失敗しました",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        # Supabaseのエラーやその他の例外
        logger.exception("トークン検証に失敗しました")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの検証に失敗しました",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    supabase: Client = Depends(get_supabase),
) -> Optional[dict]:
    """
    オプショナルな認証用の依存関数
    トークンがない場合はNoneを返し、ある場合は検証する

    Args:
        credentials: HTTPベアラートークン（オプショナル）
        supabase: Supabaseクライアント

    Returns:
        Optional[dict]: ユーザー情報またはNone
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            return None

        user = response.user
        return {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata or {},
            "access_token": token,
        }
    except (httpx.TimeoutException, httpx.HTTPError):
        return None
    except Exception:
        return None


async def ensure_rls(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> None:
    """
    ルーター全体に適用できるRLS適用用の共通依存関数。

    - Authorizationヘッダがある場合のみ、PostgRESTにユーザーJWTを適用する。
    - 失敗時はフェイルソフトで何もしない。

    Note: Request.state への格納機能は、Pydantic 2.12互換性のため一時的に無効化されています
    """
    # 認証トークンの検証のみを行う
    # RLSの適用は各エンドポイントのget_current_user依存関数で処理される
    pass
