"""
Gemini API連携サービス

Google Gemini APIを使用して旅行プランを生成します。
"""

import os
import logging
import json
from typing import Optional, Dict, Any

from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.models.plan import (
    PlanGenerateResponse,
    Route,
    Waypoint,
    RouteStep,
)

# 環境変数を読み込み
load_dotenv()

logger = logging.getLogger(__name__)

# Gemini APIの初期化
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # デフォルトは gemini-2.5-flash

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info(f"Gemini API を初期化しました (モデル: {GEMINI_MODEL})")
else:
    logger.warning("環境変数 GEMINI_API_KEY が見つかりません")


def generate_travel_plan(
    match_info: Dict[str, Any],
    current_latitude: float,
    current_longitude: float,
    transport_mode: str,
) -> PlanGenerateResponse:
    """
    Gemini APIを使用して旅行プランを生成する

    Args:
        match_info: 試合情報（opponent, venue_name, venue_latitude, venue_longitudeなど）
        current_latitude: 現在地の緯度
        current_longitude: 現在地の経度
        transport_mode: 移動手段（drive, walking, transit, bicycling）

    Returns:
        PlanGenerateResponse: 生成された旅行プラン

    Raises:
        ValueError: Gemini API keyが設定されていない場合
        Exception: Gemini API呼び出しエラー
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    # プロンプトの構築
    prompt = _build_prompt(
        match_info=match_info,
        current_latitude=current_latitude,
        current_longitude=current_longitude,
        transport_mode=transport_mode,
    )

    try:
        # Gemini モデルを使用（環境変数で設定可能）
        model = genai.GenerativeModel(GEMINI_MODEL)

        # JSON形式でのレスポンスを要求
        generation_config = GenerationConfig(
            temperature=0.7,  # 創造性を少し持たせる
            response_mime_type="application/json",
        )

        logger.info(f"Gemini API を呼び出し中: 試合={match_info.get('opponent')}")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
        )

        # レスポンスのパース
        plan_data = json.loads(response.text)
        logger.info("Gemini API から旅行プランの生成に成功しました")

        # PlanGenerateResponseに変換
        return _parse_gemini_response(plan_data)

    except json.JSONDecodeError as e:
        logger.error(f"Gemini レスポンスのJSON解析に失敗: {e}")
        logger.error(f"レスポンステキスト: {response.text if 'response' in locals() else 'N/A'}")
        raise Exception("Gemini APIからの応答をJSONとして解析できませんでした")
    except Exception as e:
        logger.error(f"Gemini API 呼び出しエラー: {e}", exc_info=True)
        raise Exception("旅行プランの生成中にエラーが発生しました")


def generate_travel_plan_stream(
    match_info: Dict[str, Any],
    current_latitude: float,
    current_longitude: float,
    transport_mode: str,
):
    """
    Gemini APIを使用してストリーミング形式で旅行プランを生成する

    Args:
        match_info: 試合情報（opponent, venue_name, venue_latitude, venue_longitudeなど）
        current_latitude: 現在地の緯度
        current_longitude: 現在地の経度
        transport_mode: 移動手段（drive, walking, transit, bicycling）

    Yields:
        str: ストリーミングで返される部分的なJSON文字列

    Raises:
        ValueError: Gemini API keyが設定されていない場合
        Exception: Gemini API呼び出しエラー
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    # プロンプトの構築
    prompt = _build_prompt(
        match_info=match_info,
        current_latitude=current_latitude,
        current_longitude=current_longitude,
        transport_mode=transport_mode,
    )

    try:
        # Gemini モデルを使用（環境変数で設定可能）
        model = genai.GenerativeModel(GEMINI_MODEL)

        # JSON形式でのレスポンスを要求
        generation_config = GenerationConfig(
            temperature=0.7,  # 創造性を少し持たせる
            response_mime_type="application/json",
        )

        logger.info(f"Gemini API ストリーミング呼び出し中: 試合={match_info.get('opponent')}")

        # ストリーミングでコンテンツを生成
        response_stream = model.generate_content(
            prompt,
            generation_config=generation_config,
            stream=True,  # ストリーミングを有効化
        )

        # ストリーミングで返ってきたテキストを順次yield
        full_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_text += chunk.text
                # 部分的なテキストをyield
                yield chunk.text

        logger.info("Gemini API ストリーミング生成が完了しました")

        # 最終的な完全なJSONをパース可能か確認（ログ用）
        try:
            json.loads(full_text)
            logger.info("生成されたJSONは有効です")
        except json.JSONDecodeError:
            logger.warning(f"生成されたJSONが不正: {full_text[:200]}...")

    except Exception as e:
        logger.error(f"Gemini API ストリーミング呼び出しエラー: {e}", exc_info=True)
        raise Exception("旅行プランのストリーミング生成中にエラーが発生しました")


def _build_prompt(
    match_info: Dict[str, Any],
    current_latitude: float,
    current_longitude: float,
    transport_mode: str,
) -> str:
    """
    Gemini APIに送信するプロンプトを構築する

    Args:
        match_info: 試合情報
        current_latitude: 現在地の緯度
        current_longitude: 現在地の経度
        transport_mode: 移動手段

    Returns:
        str: 構築されたプロンプト
    """
    transport_mode_ja = {
        "drive": "車",
        "walking": "徒歩",
        "transit": "公共交通機関",
        "bicycling": "自転車",
    }.get(transport_mode, transport_mode)

    prompt = f"""
あなたはギラヴァンツ北九州のサポーター向けに、試合観戦の旅行プランを提案するアシスタントです。
以下の情報をもとに、充実した試合観戦プランを日本語で提案してください。

# 試合情報
- 対戦相手: {match_info.get('opponent')}
- 会場: {match_info.get('venue_name')}
- 会場の位置: 緯度 {match_info.get('venue_latitude')}, 経度 {match_info.get('venue_longitude')}

# 現在地
- 緯度: {current_latitude}
- 経度: {current_longitude}

# 移動手段
- {transport_mode_ja}

# 指示
1. 現在地からスタジアムまでの楽しい旅行プランを提案してください
2. スタジアム周辺のおすすめスポット（カフェ、レストランなど）を含めてください
3. 試合前後の食事や休憩の提案も含めてください
4. ギラヴァンツ北九州のサポーター向けの熱いメッセージも添えてください

# 出力形式（必須）
必ずJSON形式で以下の構造で返してください：

{{
  "plan_text": "プランの詳細な説明文（日本語、改行を含む）",
  "route": {{
    "waypoints": [
      {{
        "name": "現在地",
        "latitude": {current_latitude},
        "longitude": {current_longitude},
        "store_id": null
      }},
      {{
        "name": "おすすめスポット名",
        "latitude": おすすめスポットの緯度,
        "longitude": おすすめスポットの経度,
        "store_id": null
      }},
      {{
        "name": "{match_info.get('venue_name')}",
        "latitude": {match_info.get('venue_latitude')},
        "longitude": {match_info.get('venue_longitude')},
        "store_id": null
      }}
    ],
    "total_duration_minutes": 合計所要時間（分）,
    "steps": [
      {{
        "from": "現在地",
        "to": "おすすめスポット名",
        "transport": "{transport_mode}",
        "duration_minutes": 所要時間（分）
      }},
      {{
        "from": "おすすめスポット名",
        "to": "{match_info.get('venue_name')}",
        "transport": "{transport_mode}",
        "duration_minutes": 所要時間（分）
      }}
    ]
  }}
}}

重要: 必ず有効なJSON形式で応答してください。JSONの外に追加のテキストを含めないでください。
"""
    return prompt


def _parse_gemini_response(plan_data: Dict[str, Any]) -> PlanGenerateResponse:
    """
    Gemini APIのレスポンスをPydanticモデルに変換する

    Args:
        plan_data: Gemini APIからのJSON応答

    Returns:
        PlanGenerateResponse: パースされた旅行プラン
    """
    try:
        # waypointsの変換
        waypoints = [
            Waypoint(
                name=wp["name"],
                latitude=float(wp["latitude"]),
                longitude=float(wp["longitude"]),
                store_id=wp.get("store_id"),
            )
            for wp in plan_data["route"]["waypoints"]
        ]

        # stepsの変換（aliasに対応するため、model_validateを使用）
        steps = [
            RouteStep.model_validate(step)
            for step in plan_data["route"]["steps"]
        ]

        # Routeの構築
        route = Route(
            waypoints=waypoints,
            total_duration_minutes=int(plan_data["route"]["total_duration_minutes"]),
            steps=steps,
        )

        # PlanGenerateResponseの構築
        return PlanGenerateResponse(
            plan_text=plan_data["plan_text"],
            route=route,
        )

    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Gemini レスポンスのパースに失敗: {e}")
        logger.error(f"プランデータ: {plan_data}")
        raise Exception("Gemini APIの応答形式が不正です")
