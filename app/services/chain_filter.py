"""
Chain store filtering helpers.

These utilities provide a lightweight way to exclude known chain brands
from search results when looking for local stores.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, TypeVar, Callable
from functools import lru_cache

from app.services.supabase_client import get_client


# A non-exhaustive list of chain brand keywords (case-insensitive).
CHAIN_KEYWORDS: Sequence[str] = (
    "mcdonald",  # McDonald's
    "starbucks",
    "kfc",
    "yoshinoya",
    "coco ichi",  # CoCo Ichibanya
    "cocoichi",
    "sukiya",
    "matsuya",
    "mos burger",
    "saizeriya",
    "royal host",
    "denny's",
    "big boy",
    "jonathan",
    "kentucky",
    "kura sushi",
    "sushiro",
    "kappa sushi",
    "hamazushi",
    "yayoiken",
    "skylark",
    "joyfull",
    "gusto",
)


def is_chain_store(name: str, *, keywords: Sequence[str] = CHAIN_KEYWORDS) -> bool:
    """Return True if ``name`` likely represents a chain brand.

    The check is a simple case-insensitive substring search against a curated
    keyword list.
    """

    lower = name.lower()
    return any(k in lower for k in keywords)


T = TypeVar("T")


def filter_out_chain_items(items: Iterable[T], get_name: Callable[[T], str]) -> List[T]:
    """Filter out items whose name matches chain store keywords.

    Args:
        items: Input iterable of items.
        get_name: Function to extract the display name from each item.

    Returns:
        A list containing only items considered non-chain.
    """

    result: List[T] = []
    for item in items:
        try:
            name = get_name(item)
        except Exception:
            # If name extraction fails, keep the item conservatively.
            result.append(item)
            continue
        if not is_chain_store(name):
            result.append(item)
    return result


def _merge_keywords(extra: Sequence[str]) -> List[str]:
    base = [k.lower() for k in CHAIN_KEYWORDS]
    base.extend([k.lower() for k in extra if k])
    # 重複を削除し、安定順序を維持
    seen = set()
    merged: List[str] = []
    for k in base:
        if k not in seen:
            seen.add(k)
            merged.append(k)
    return merged


def filter_out_chain_items_dyn(
    items: Iterable[T], get_name: Callable[[T], str], *, extra_keywords: Sequence[str]
) -> List[T]:
    """チェーンワード（静的+動的）でフィルタリングする。

    extra_keywords: DB由来のチェーン店名などを渡す。
    """
    keywords = _merge_keywords(extra_keywords)
    result: List[T] = []
    for item in items:
        try:
            name = get_name(item)
        except Exception:
            result.append(item)
            continue
        lower = name.lower()
        if not any(k in lower for k in keywords):
            result.append(item)
    return result


@lru_cache(maxsize=1)
def get_dynamic_chain_keywords() -> List[str]:
    """DBのchain_storesから名称を取得。取得失敗時は空配列。

    短時間での再呼び出しはキャッシュする。
    """
    client = get_client()
    if client is None:
        return []
    try:
        resp = client.table("chain_stores").select("name").execute()
        rows = getattr(resp, "data", None) or []
        names: List[str] = []
        for r in rows:
            n = r.get("name")
            if isinstance(n, str) and n.strip():
                names.append(n.strip())
        return names
    except Exception:
        return []

