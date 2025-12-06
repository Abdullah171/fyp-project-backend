# app/routers/settings.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..utils.settings import get_or_create_global_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=schemas.SettingsOut)
def read_settings(db: Session = Depends(get_db)):
    s = get_or_create_global_settings(db)
    return schemas.SettingsOut(
        filter_mode=s.filter_mode,
        parental_controls=s.parental_controls,
        notifications=s.notifications,
        save_search_history=s.save_search_history,
        blocked_keywords=s.blocked_keywords or "",
        allowed_domains=s.allowed_domains or "",
    )


@router.put("", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsUpdate, db: Session = Depends(get_db)):
    s = get_or_create_global_settings(db)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(s, field, value)
    db.add(s)
    db.commit()
    db.refresh(s)

    return schemas.SettingsOut(
        filter_mode=s.filter_mode,
        parental_controls=s.parental_controls,
        notifications=s.notifications,
        save_search_history=s.save_search_history,
        blocked_keywords=s.blocked_keywords or "",
        allowed_domains=s.allowed_domains or "",
    )
