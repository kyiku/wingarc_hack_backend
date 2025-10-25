"""
Serena MCP 関連の疎通確認 API。

現時点では設定状況を返すのみの軽量エンドポイントです。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services.serena_mcp import get_serena_mcp_config


router = APIRouter(prefix="/serena", tags=["Serena MCP"])


@router.get("/config")
def get_config() -> dict:
    """Serena MCP の設定状況を返す。

    Returns:
        dict: command/args/workdir と configured フラグ
    """
    cfg = get_serena_mcp_config()
    return cfg.as_dict()

