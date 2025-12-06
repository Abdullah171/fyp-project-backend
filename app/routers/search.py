# app/routers/search.py
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
from .. import models, schemas
from ..database import get_db
from ..services.search_providers import get_provider
from ..services.filtering import filter_results, classify_result_type
from ..utils.settings import get_or_create_global_settings

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=List[schemas.SearchResultOut])
def perform_search(
    payload: schemas.SearchRequest,
    db: Session = Depends(get_db),
):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    provider = get_provider()

    try:
        raw_results = provider.search(payload.query, limit=payload.limit)
    except requests.HTTPError as e:
        # upstream provider like Wikipedia failed
        raise HTTPException(
            status_code=502,
            detail=f"Upstream search provider error: {e.response.status_code}",
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Failed to contact upstream search provider",
        )

    raw_results = provider.search(payload.query, limit=payload.limit)

    settings = get_or_create_global_settings(db)
    effective_mode = payload.filter_mode or settings.filter_mode

    filtered, blocked_count = filter_results(
        raw_results,
        filter_mode=effective_mode,
        blocked_keywords=settings.blocked_keywords or "",
        allowed_domains=settings.allowed_domains or "",
    )

    total = len(raw_results)
    safe = len(filtered)

    # if we don't save history, just return
    if not settings.save_search_history:
        now = datetime.utcnow()
        out: List[schemas.SearchResultOut] = []
        for idx, r in enumerate(filtered, start=1):
            out.append(
                schemas.SearchResultOut(
                    id=idx,
                    title=r["title"],
                    url=r["url"],
                    snippet=r["snippet"],
                    type=classify_result_type(r["url"]),
                    timestamp=now,
                )
            )
        return out

    # save query + results
    q = models.SearchQuery(
        query=payload.query,
        filter_mode=effective_mode,
        total_results=total,
        safe_results=safe,
        blocked_results=blocked_count,
    )
    db.add(q)
    db.flush()  # so q.id is available

    for r in filtered:
        db.add(
            models.SearchResult(
                query_id=q.id,
                title=r["title"],
                url=r["url"],
                snippet=r["snippet"],
                type=classify_result_type(r["url"]),
                is_blocked=False,
            )
        )

    db.commit()
    db.refresh(q)

    return [
        schemas.SearchResultOut(
            id=row.id,
            title=row.title,
            url=row.url,
            snippet=row.snippet,
            type=row.type,
            timestamp=row.created_at,
        )
        for row in q.results
    ]
