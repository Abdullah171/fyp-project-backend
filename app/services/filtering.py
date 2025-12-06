# app/services/filtering.py
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from ..models import FilterMode, ResultType


# Very simple keyword lists – you can extend these
STRICT_KEYWORDS = {"sex", "porn", "adult", "nsfw", "xxx", "erotic"}
MODERATE_KEYWORDS = {"porn", "nsfw", "xxx"}

# 🔥 Relaxed should NOT block porn etc by default
RELAXED_KEYWORDS: set[str] = set()

def get_base_keywords(mode: FilterMode) -> set[str]:
    if mode == FilterMode.strict:
        return STRICT_KEYWORDS
    if mode == FilterMode.moderate:
        return MODERATE_KEYWORDS
    # relaxed: no base keyword blocking
    return RELAXED_KEYWORDS


def text_contains_banned(text: str, banned: set[str]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in banned)


def parse_csv(text: str) -> List[str]:
    if not text:
        return []
    return [x.strip().lower() for x in text.split(",") if x.strip()]


def filter_results(
    raw_results: List[Dict],
    filter_mode: FilterMode,
    blocked_keywords: str,
    allowed_domains: str,
) -> Tuple[List[Dict], int]:
    base_keywords = get_base_keywords(filter_mode)
    extra_blocked = set(parse_csv(blocked_keywords))
    banned = base_keywords.union(extra_blocked)

    allowed = set(parse_csv(allowed_domains))

    filtered: List[Dict] = []
    blocked_count = 0

    for r in raw_results:
        url = r["url"]
        text = f"{r['title']} {r['snippet']}"
        domain = (urlparse(url).hostname or "").lower()

        # If allowed_domains defined, only allow those
        if allowed and domain not in allowed:
            blocked_count += 1
            continue

        if text_contains_banned(text, banned):
            blocked_count += 1
            continue

        filtered.append(r)

    return filtered, blocked_count


def classify_result_type(url: str) -> ResultType:
    u = url.lower()
    if "youtube.com" in u or "vimeo.com" in u:
        return ResultType.video
    if any(ext in u for ext in [".jpg", ".jpeg", ".png", ".gif"]):
        return ResultType.image
    return ResultType.text
