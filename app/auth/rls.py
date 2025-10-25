"""
RLS適用用の関数デコレーター

FastAPIの依存解決で渡される `current_user` と `supabase` を利用して、
PostgREST にエンドユーザーJWTを適用するクロスカッティングな仕組みを提供します。

注意:
- デコレーターを使う場合、エンドポイント関数のシグネチャに
  `current_user: dict = Depends(get_current_user)` と
  `supabase: Client = Depends(get_supabase)` を含めてください。
- 既にルーター依存関数で RLS を有効化している場合（ensure_rls）と重複適用しても
  害はありませんが、どちらか一方へ統一することを推奨します。
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Awaitable, Callable

try:
    from supabase import Client  # type: ignore
except Exception:  # pragma: no cover
    Client = object  # type: ignore


def with_rls(func: Callable[..., Awaitable[Any]]):
    """エンドポイント実行前にPostgRESTへユーザーJWTを適用するデコレーター。

    期待する引数:
        - current_user: dict （get_current_user によって注入）
        - supabase: Client （get_supabase によって注入）
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        supabase: Client | None = kwargs.get("supabase")
        current_user = kwargs.get("current_user") or {}
        token = ""
        try:
            token = current_user.get("access_token", "")
        except Exception:
            token = ""

        try:
            if supabase is not None:
                postgrest = getattr(supabase, "postgrest", None)
                if postgrest and hasattr(postgrest, "auth"):
                    postgrest.auth(token)
        except Exception:
            # フェイルソフト: JWT適用に失敗しても処理は継続
            pass

        return await func(*args, **kwargs)

    # FastAPI が依存解決に利用するシグネチャを保持
    try:
        wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
    except Exception:
        pass
    return wrapper

