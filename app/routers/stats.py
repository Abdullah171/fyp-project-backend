# app/routers/stats.py
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=schemas.OverviewStats)
def overview(db: Session = Depends(get_db)):
    total_searches = db.query(func.count(models.SearchQuery.id)).scalar() or 0
    blocked_content = (
        db.query(func.coalesce(func.sum(models.SearchQuery.blocked_results), 0)).scalar()
        or 0
    )
    safe_results = (
        db.query(func.coalesce(func.sum(models.SearchQuery.safe_results), 0)).scalar()
        or 0
    )

    # simple heuristic: ~1 minute per search
    active_time_hours = round(total_searches / 60.0, 2)

    return schemas.OverviewStats(
        total_searches=total_searches,
        blocked_content=blocked_content,
        safe_results=safe_results,
        active_time_hours=active_time_hours,
    )


@router.get("/recent", response_model=List[schemas.ActivityItem])
def recent(db: Session = Depends(get_db), limit: int = 10):
    rows = (
        db.query(models.SearchQuery)
        .order_by(models.SearchQuery.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        schemas.ActivityItem(
            id=row.id,
            query=row.query,
            created_at=row.created_at,
            safe_results=row.safe_results,
            blocked_results=row.blocked_results,
        )
        for row in rows
    ]
