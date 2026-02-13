# app/routers/history.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.responses import StreamingResponse
import csv
from io import StringIO

from ..database import get_db
from .. import models

router = APIRouter(prefix="/history", tags=["history"])


@router.delete("")
def clear_search_history(db: Session = Depends(get_db)):
    # Delete results first (if FK cascade is not fully enforced in your DB)
    db.query(models.SearchResult).delete(synchronize_session=False)
    deleted_queries = db.query(models.SearchQuery).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "deleted_queries": deleted_queries}


@router.get("/export.csv")
def export_history_csv(db: Session = Depends(get_db)):
    """
    Exports SearchQuery rows as CSV (basic audit trail).
    Extend this if you want to include SearchResult rows too.
    """
    rows = (
        db.query(models.SearchQuery)
        .order_by(models.SearchQuery.created_at.desc())
        .all()
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "query", "created_at", "filter_mode", "total_results", "safe_results", "blocked_results"])

    for r in rows:
        writer.writerow([
            r.id,
            r.query,
            r.created_at.isoformat(),
            r.filter_mode.value if hasattr(r.filter_mode, "value") else str(r.filter_mode),
            r.total_results,
            r.safe_results,
            r.blocked_results,
        ])

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=search_history.csv"},
    )
