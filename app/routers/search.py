# app/routers/search.py
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
from typing import Dict
from .. import models, schemas
from ..database import get_db
from ..services.search_providers import get_provider
from ..services.filtering import filter_results, classify_result_type
from ..utils.settings import get_or_create_global_settings
from ..models import ResultType  

router = APIRouter(prefix="/search", tags=["search"])



def infer_result_type(r: Dict) -> ResultType:
  """
  Prefer 'image' if we have a preview_url (img_src/thumbnail from SearxNG).
  Otherwise fall back to URL-based classification.
  """
  if r.get("preview_url"):
      return ResultType.image
  return classify_result_type(r["url"])



@router.post("", response_model=schemas.SearchResponse)
def perform_search(
    payload: schemas.SearchRequest,
    db: Session = Depends(get_db),
):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    provider = get_provider()

    try:
        raw_results = provider.search(payload.query, limit=payload.limit)
        has_more = len(raw_results) == payload.limit
    except requests.HTTPError as e:
        # Upstream returned HTTP error (e.g. 500)
        logger.exception("Upstream search provider HTTP error")
        # 👉 Either raise 502 (strict)...
        # raise HTTPException(
        #     status_code=502,
        #     detail=f"Upstream search provider error: {e.response.status_code}",
        # )
        # ...or degrade gracefully:
        return schemas.SearchResponse(results=[], has_more=False)
    except requests.RequestException as e:
        # Timeouts / connection issues / DNS, etc.
        logger.exception("Failed to contact upstream search provider")
        # 👉 Again, either raise...
        # raise HTTPException(
        #     status_code=502,
        #     detail=f"Failed to contact upstream search provider: {e}",
        # )
        # ...or degrade gracefully:
        return schemas.SearchResponse(results=[], has_more=False)

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

    # CASE 1: Don't save history; just respond
    if not settings.save_search_history:
        now = datetime.utcnow()
        out: List[schemas.SearchResultOut] = []
        for idx, r in enumerate(filtered, start=1):
            url = (r.get("url") or "").strip()
            if not url:
                # skip results with no URL
                continue

            out.append(
                schemas.SearchResultOut(
                    id=idx,
                    title=r["title"],
                    url=url,
                    snippet=r["snippet"],
                    type=infer_result_type(r),
                    timestamp=now,
                    preview_url=r.get("preview_url"),
                )
            )
        return schemas.SearchResponse(results=out, has_more=has_more)


    # CASE 2: Save query + results but still return "live" preview URLs
    q = models.SearchQuery(
        query=payload.query,
        filter_mode=effective_mode,
        total_results=total,
        safe_results=safe,
        blocked_results=blocked_count,
    )
    db.add(q)
    db.flush()

    db_results: List[models.SearchResult] = []
    for r in filtered:
        url = (r.get("url") or "").strip()
        if not url:
            continue

        row = models.SearchResult(
            query_id=q.id,
            title=r["title"],
            url=url,
            snippet=r["snippet"],
            type=infer_result_type(r),
            is_blocked=False,
        )
        db.add(row)
        db_results.append(row)


    db.commit()
    db.refresh(q)

    out: List[schemas.SearchResultOut] = []
    for r, row in zip(filtered, db_results):
        out.append(
            schemas.SearchResultOut(
                id=row.id,
                title=row.title,
                url=row.url,
                snippet=row.snippet,
                type=row.type,
                timestamp=row.created_at,
                preview_url=r.get("preview_url"),
            )
        )
    return schemas.SearchResponse(results=out, has_more=has_more)