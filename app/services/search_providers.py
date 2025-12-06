# app/services/search_providers.py
from typing import List, Dict, Optional
from urllib.parse import quote_plus

import requests

from ..config import settings


class BaseProvider:
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        raise NotImplementedError


class WikipediaProvider(BaseProvider):
    API_URL = "https://en.wikipedia.org/w/api.php"

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": limit,
        }

        headers = {
            "User-Agent": "NetSentinelSafeSearch/1.0 (student project; contact: youremail@example.com)"
        }

        resp = requests.get(self.API_URL, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        out: List[Dict] = []

        for item in data.get("query", {}).get("search", []):
            title = item["title"]
            snippet = item["snippet"]
            url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

            clean_snippet = (
                snippet.replace('<span class="searchmatch">', "")
                .replace("</span>", "")
                .replace("&quot;", '"')
            )

            out.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": clean_snippet,
                    # wikipedia has no image thumbnail in this API
                    "preview_url": None,
                }
            )

        return out


class SearxNGProvider(BaseProvider):
    """
    Calls your SearxNG instance /search?format=json and normalizes the results
    to {title, url, snippet, preview_url}.
    """

    def __init__(self, base_url: Optional[str] = None, categories: Optional[str] = None):
        self.base_url = (base_url or settings.SEARXNG_URL).rstrip("/")
        self.categories = categories or settings.SEARXNG_CATEGORIES

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        params = {
            "q": query,
            "format": "json",
            "categories": self.categories,
            "language": "en",
            # OLD:
            # "safesearch": 2,
            # NEW: let our own filters + NudeNet do the work
            "safesearch": 0,
        }

        url = f"{self.base_url}/search"
        headers = {
            "User-Agent": "NetSentinelSafeSearch/1.0 (student project; contact: youremail@example.com)"
        }

        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        raw_results: List[Dict] = []
        for item in data.get("results", [])[:limit]:
            title = item.get("title") or item.get("url") or "Untitled"
            snippet = item.get("content") or ""
            result_url = item.get("url") or ""
            # try to find an image thumb from SearxNG
            img = item.get("img_src") or item.get("thumbnail") or None

            # IMPORTANT:
            # We always expose image URLs through our own /api/media/proxy endpoint,
            # so the frontend never hits the original URL directly.
            preview_url: Optional[str] = None
            if img:
                encoded = quote_plus(img)
                preview_url = f"/api/media/proxy?url={encoded}"

            raw_results.append(
                {
                    "title": title,
                    "url": result_url,
                    "snippet": snippet,
                    "preview_url": preview_url,
                }
            )

        return raw_results


_provider_singleton: BaseProvider | None = None


def get_provider() -> BaseProvider:
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton

    if settings.SEARCH_PROVIDER.lower() == "searxng":
        _provider_singleton = SearxNGProvider()
    elif settings.SEARCH_PROVIDER.lower() == "wikipedia":
        _provider_singleton = WikipediaProvider()
    else:
        # fallback
        _provider_singleton = SearxNGProvider()

    return _provider_singleton
