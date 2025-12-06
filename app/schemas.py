# app/schemas.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl

from .models import FilterMode, ResultType


class SearchRequest(BaseModel):
    query: str
    filter_mode: Optional[FilterMode] = None
    limit: int = 10


class SearchResultOut(BaseModel):
    id: int
    title: str
    url: HttpUrl
    snippet: str
    type: ResultType
    timestamp: datetime

    # NEW: relative or absolute URL to a (possibly blurred) thumbnail
    # For SearxNG this will look like: /api/media/proxy?url=<encoded_remote_url>
    preview_url: Optional[str] = None

    class Config:
        orm_mode = True

        
class SearchResponse(BaseModel):
    results: List[SearchResultOut]
    has_more: bool


class SettingsOut(BaseModel):
    filter_mode: FilterMode
    parental_controls: bool
    notifications: bool
    save_search_history: bool
    blocked_keywords: str
    allowed_domains: str


class SettingsUpdate(BaseModel):
    filter_mode: Optional[FilterMode] = None
    parental_controls: Optional[bool] = None
    notifications: Optional[bool] = None
    save_search_history: Optional[bool] = None
    blocked_keywords: Optional[str] = None
    allowed_domains: Optional[str] = None


class OverviewStats(BaseModel):
    total_searches: int
    blocked_content: int
    safe_results: int
    active_time_hours: float


class ActivityItem(BaseModel):
    id: int
    query: str
    created_at: datetime
    safe_results: int
    blocked_results: int
