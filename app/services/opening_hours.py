"""
Opening hours parser

開店時間のJSON表現（文字列配列 / オブジェクト配列 / オブジェクト）を
Pydanticで検証して、`List[str]` に正規化するヘルパー。
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, RootModel, ValidationError


class OpeningHoursList(RootModel):
    root: List[str]


class OpeningHoursDict(BaseModel):
    weekday_text: List[str]


class OpeningHoursEntry(BaseModel):
    weekday_text: Optional[str] = None
    text: Optional[str] = None


class OpeningHoursEntryList(RootModel):
    root: List[OpeningHoursEntry]


def normalize_opening_hours(raw: Any) -> Optional[List[str]]:
    """様々な形状の開店時間表現を `List[str]` に正規化する。

    受け入れる形状:
      - List[str]
      - List[{ weekday_text?: str, text?: str }]
      - { weekday_text: List[str] }
    パースできない場合は None を返す。
    """
    if raw is None:
        return None
    # パターン1: 文字列配列
    try:
        return OpeningHoursList.model_validate(raw).root
    except ValidationError:
        pass

    # パターン2: { weekday_text: [...] }
    try:
        return OpeningHoursDict.model_validate(raw).weekday_text
    except ValidationError:
        pass

    # パターン3: オブジェクト配列から代表テキストを抽出
    try:
        entries = OpeningHoursEntryList.model_validate(raw).root
        result: List[str] = []
        for e in entries:
            s = e.weekday_text or e.text
            if isinstance(s, str) and s:
                result.append(s)
        return result or None
    except ValidationError:
        return None


def parse_opening_hours(raw: Optional[object]) -> Optional[List[str]]:
    """エイリアス関数: 提案のシグネチャに合わせた薄いラッパー"""
    return normalize_opening_hours(raw)
