"""
Chain store filtering helpers.

These utilities provide a lightweight way to exclude known chain brands
from search results when looking for local stores.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, TypeVar, Callable


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

