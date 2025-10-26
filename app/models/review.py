"""
レビュー関連のモデル
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class ReviewCreate(BaseModel):
    """レビュー作成リクエスト"""
    rating: int = Field(..., ge=1, le=5, description="評価（1-5）")
    comment: str = Field(..., min_length=1, max_length=1000, description="コメント")
    # 店舗情報（DBに未登録の店舗の場合に自動登録するために使用）
    store_name: Optional[str] = Field(None, description="店舗名")
    store_latitude: Optional[float] = Field(None, description="緯度")
    store_longitude: Optional[float] = Field(None, description="経度")
    store_google_place_id: Optional[str] = Field(None, description="Google Place ID")


class ReviewResponse(BaseModel):
    """レビューレスポンス"""
    id: UUID
    store_id: UUID
    user_id: UUID
    user_name: str
    rating: int
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}
