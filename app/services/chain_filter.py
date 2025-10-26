"""
Chain store filtering helpers.

These utilities provide a lightweight way to exclude known chain brands
from search results when looking for local stores.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, TypeVar, Callable
import os
import time
import threading
import httpx
from postgrest.exceptions import APIError

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


_CACHE_LOCK = threading.Lock()
_CACHED_NAMES: List[str] = []
_CACHED_AT: float = 0.0


def _ttl_seconds() -> int:
    """キャッシュTTL（秒）。環境変数 `CHAIN_KEYWORDS_TTL_SECONDS` で上書き可能。"""
    try:
        return int(os.getenv("CHAIN_KEYWORDS_TTL_SECONDS", "300"))
    except Exception:
        return 300


def get_dynamic_chain_keywords() -> List[str]:
    """DBのchain_storesから名称を取得（TTLキャッシュ）。

    - 取得失敗時は前回成功時の値を返す。初回かつ失敗なら空配列。
    - デフォルトTTLは300秒。環境変数で調整可能。
    """
    global _CACHED_AT
    now = time.monotonic()
    # まずはロックなしで期限切れ判定（高速経路）
    if _CACHED_NAMES and (now - _CACHED_AT) < _ttl_seconds():
        return list(_CACHED_NAMES)

    with _CACHE_LOCK:
        # ロック獲得後に再判定（他スレッドが更新済みかもしれない）
        if _CACHED_NAMES and (now - _CACHED_AT) < _ttl_seconds():
            return list(_CACHED_NAMES)

        client = get_client()
        if client is None:
            # クライアント未設定: 既存キャッシュがあればそれを返す、なければ空
            return list(_CACHED_NAMES) if _CACHED_NAMES else []
        try:
            resp = client.table("chain_stores").select("name").execute()
            rows = getattr(resp, "data", None) or []
            names: List[str] = []
            for r in rows:
                n = r.get("name")
                if isinstance(n, str) and n.strip():
                    names.append(n.strip())
            # 正常取得: キャッシュ更新
            _CACHED_NAMES.clear()
            _CACHED_NAMES.extend(names)
            _CACHED_AT = now
            return list(_CACHED_NAMES)
        except (httpx.TimeoutException, httpx.HTTPError, APIError):
            return list(_CACHED_NAMES) if _CACHED_NAMES else []
        except Exception:
            # 失敗時: 既存キャッシュを返す（なければ空）
            return list(_CACHED_NAMES) if _CACHED_NAMES else []


def invalidate_dynamic_chain_keywords_cache() -> None:
    """チェーン店名キャッシュを即時クリアする。"""
    global _CACHED_AT
    with _CACHE_LOCK:
        _CACHED_NAMES.clear()
        _CACHED_AT = 0.0


def refresh_dynamic_chain_keywords() -> List[str]:
    """キャッシュを無視してDBから再取得し、最新値でキャッシュを更新して返す。"""
    global _CACHED_AT
    with _CACHE_LOCK:
        client = get_client()
        if client is None:
            _CACHED_NAMES.clear()
            _CACHED_AT = 0.0
            return []
        try:
            resp = client.table("chain_stores").select("name").execute()
            rows = getattr(resp, "data", None) or []
            names: List[str] = []
            for r in rows:
                n = r.get("name")
                if isinstance(n, str) and n.strip():
                    names.append(n.strip())
            _CACHED_NAMES.clear()
            _CACHED_NAMES.extend(names)
            _CACHED_AT = time.monotonic()
            return list(_CACHED_NAMES)
        except (httpx.TimeoutException, httpx.HTTPError, APIError):
            # 失敗時はキャッシュを変更しない
            return list(_CACHED_NAMES)
        except Exception:
            # 失敗時はキャッシュを変更しない
            return list(_CACHED_NAMES)

