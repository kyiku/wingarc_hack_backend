"""
Gemini API を用いたプラン生成サービス。

環境変数 GEMINI_API_KEY が設定されている場合のみ実呼び出しを行い、
失敗時は呼び出し側でダミー応答へフォールバックできるよう例外を透過する。
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from app.models.plan import (
    PlanGenerateRequest,
    PlanGenerateResponse,
)


_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def _ensure_client():
    """google-generativeai を初期化して Model を返す。"""
    import google.generativeai as genai  # lazy import

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY が未設定です")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(_MODEL_NAME)


def _build_prompt(match: Dict[str, Any], req: PlanGenerateRequest) -> str:
    """JSONで PlanGenerateResponse 互換の出力を指示するプロンプトを生成。"""

    md = match or {}
    opponent = md.get("opponent", "対戦相手不明")
    venue_name = md.get("venue_name", "会場不明")
    venue_lat = md.get("venue_latitude")
    venue_lng = md.get("venue_longitude")
    match_dt = md.get("match_datetime")

    prompt = f"""
あなたはJリーグ観戦の地元ガイドです。安全で実用的な移動と食事・休憩を提案してください。

制約:
- 出力は必ずJSONのみ。説明文やコードフェンスは出力しない。
- JSONスキーマは以下に厳密に従うこと。
  {{
    "plan_text": string,
    "route": {{
      "waypoints": [
        {{"name": string, "latitude": number, "longitude": number, "store_id": null}} , ...
      ],
      "total_duration_minutes": integer,
      "steps": [
        {{"from": string, "to": string, "transport": string, "duration_minutes": integer}}, ...
      ]
    }}
  }}

入力情報:
- 現在地: lat={req.current_latitude}, lng={req.current_longitude}
- 移動手段: {req.transport_mode.value}
- 試合: {opponent} 戦, 開催日時={match_dt}
- 会場: {venue_name} (lat={venue_lat}, lng={venue_lng})

要件:
- 会場到着を優先し、到着までの移動ステップを必ず含める。
- 所要時間合計も整合的にする。
- waypoints は最低でも 現在地 → 会場 の2点を含める。
- 日本語で丁寧に、過度に長文にしない。
"""
    return prompt


def _extract_json(text: str) -> Dict[str, Any]:
    """大抵の生成結果に混ざるコードフェンスなどを考慮してJSON部分を抜き出す。"""
    s = text.strip()
    # ```json ... ``` の除去
    if s.startswith("```"):
        # 先頭のフェンスを1つ落とす
        first_newline = s.find("\n")
        s = s[first_newline + 1 :] if first_newline != -1 else s
        if s.endswith("```"):
            s = s[: -3]
    # 最初の '{' から最後の '}' までを抽出（単純だが堅牢性が高い）
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    return json.loads(s)


def generate_plan(match: Dict[str, Any], req: PlanGenerateRequest) -> PlanGenerateResponse:
    """Geminiでプランを生成し、Pydanticで厳密に検証して返す。"""
    model = _ensure_client()
    prompt = _build_prompt(match, req)
    result = model.generate_content(prompt)
    text = getattr(result, "text", None) or ""
    data = _extract_json(text)
    return PlanGenerateResponse.model_validate(data)

