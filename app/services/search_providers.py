# app/services/search_providers.py
from typing import List, Dict

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

        # 👇 This is the important part
        headers = {
            "User-Agent": "NetSentinelSafeSearch/1.0 (student project; contact: youremail@example.com)"
        }

        resp = requests.get(self.API_URL, params=params, headers=headers, timeout=5)
        resp.raise_for_status()  # will raise if still 403/500/etc
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
                }
            )

        return out


_provider_singleton: BaseProvider | None = None


def get_provider() -> BaseProvider:
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton

    if settings.SEARCH_PROVIDER == "wikipedia":
        _provider_singleton = WikipediaProvider()
    else:
        _provider_singleton = WikipediaProvider()

    return _provider_singleton
