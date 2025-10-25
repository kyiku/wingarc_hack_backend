"""
DB行を型安全に扱うための軽量Pydanticモデル

Supabaseの `select()` 結果を都度 `dict` で扱う代わりに、
最小限のスキーマをPydanticで検証してコードの簡潔性と堅牢性を高める。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StoreIdMapRow(BaseModel):
    """storesテーブルの id と google_place_id のペア"""

    id: str = Field(description="stores.id")
    google_place_id: str = Field(description="stores.google_place_id")


class StoreIdOnlyRow(BaseModel):
    """store_idだけを含む行（reviews, player_recommendations など）"""

    store_id: str = Field(description="対象テーブルの store_id")

