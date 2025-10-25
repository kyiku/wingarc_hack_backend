"""
レビュー関連のモデル
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class ReviewCreate(BaseModel):
    """レビュー作成リクエスト"""
    rating: int = Field(..., ge=1, le=5, description="評価（1-5）")
    comment: str = Field(..., min_length=1, max_length=1000, description="コメント")


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
