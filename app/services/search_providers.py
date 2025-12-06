# app/services/search_providers.py
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlparse, urlunparse

import requests

from ..config import settings


class BaseProvider:
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        raise NotImplementedError


class SearxNGProvider(BaseProvider):
    """
    Calls your SearxNG instance /search?format=json and normalizes the results
    to {title, url, snippet, preview_url}.
    """

    def __init__(self, base_url: Optional[str] = None, categories: Optional[str] = None):
        self.base_url = (base_url or settings.SEARXNG_URL).rstrip("/")
        self.categories = categories or settings.SEARXNG_CATEGORIES

    def _normalize_img_url(self, img: str) -> str:
        if not img:
            return img

        parsed_img = urlparse(img)
        base = urlparse(self.base_url)  # e.g. http://searxng:8080

        # if searx gave us localhost/127.0.0.1 or missing host,
        # swap to the container host from SEARXNG_URL
        if parsed_img.hostname in ("localhost", "127.0.0.1") or not parsed_img.netloc:
            parsed_img = parsed_img._replace(scheme=base.scheme, netloc=base.netloc)
            img = urlunparse(parsed_img)

        return img

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        params = {
            "q": query,
            "format": "json",
            "categories": self.categories,
            "language": "en",
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

            img = item.get("img_src") or item.get("thumbnail") or None
            preview_url: Optional[str] = None

            if img:
                img = self._normalize_img_url(img)
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
    else:
        # fallback
        _provider_singleton = SearxNGProvider()

    return _provider_singleton
