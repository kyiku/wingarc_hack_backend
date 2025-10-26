"""
旅行プラン関連のモデル
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional
from enum import Enum


class TransportMode(str, Enum):
    """交通手段の列挙型"""
    DRIVE = "drive"
    WALKING = "walking"
    TRANSIT = "transit"
    BICYCLING = "bicycling"


# ========== プラン生成 ==========

class PlanGenerateRequest(BaseModel):
    """AI旅行プラン生成リクエスト"""
    match_id: UUID = Field(..., description="試合ID")
    current_latitude: float = Field(..., ge=-90, le=90, description="現在地の緯度")
    current_longitude: float = Field(..., ge=-180, le=180, description="現在地の経度")
    transport_mode: TransportMode = Field(
        TransportMode.DRIVE, description="移動手段（drive, walking, transit, bicycling）"
    )


class Waypoint(BaseModel):
    """経路のウェイポイント"""
    name: str
    latitude: float
    longitude: float
    store_id: Optional[UUID] = None


class RouteStep(BaseModel):
    """経路のステップ"""
    from_: str = Field(..., alias="from", description="出発地点")
    to: str = Field(..., description="到着地点")
    transport: str = Field(..., description="移動手段")
    duration_minutes: int = Field(..., description="所要時間（分）")


class Route(BaseModel):
    """生成された経路情報"""
    waypoints: List[Waypoint]
    total_duration_minutes: int
    steps: List[RouteStep]


class PlanGenerateResponse(BaseModel):
    """AI旅行プラン生成レスポンス"""
    plan_text: str = Field(..., description="生成されたプランのテキスト")
    route: Route = Field(..., description="経路情報")


# ========== プラン保存・取得 ==========

class PlanCreate(BaseModel):
    """プラン作成リクエスト"""
    match_id: UUID = Field(..., description="試合ID")
    title: str = Field(..., min_length=1, max_length=200, description="プランのタイトル")
    plan_details: str = Field(..., description="プランの詳細")
    route_data: Optional[Dict[str, Any]] = Field(None, description="ルート情報（JSON形式）")


class PlanListResponse(BaseModel):
    """プラン一覧レスポンス"""
    id: UUID
    match_id: UUID
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanResponse(BaseModel):
    """プラン詳細レスポンス"""
    id: UUID
    user_id: UUID
    match_id: UUID
    title: str
    plan_details: str
    route_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}
