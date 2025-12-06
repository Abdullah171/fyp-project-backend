# app/utils/settings.py
from sqlalchemy.orm import Session

from .. import models


def get_or_create_global_settings(db: Session) -> models.GlobalSettings:
    existing = db.query(models.GlobalSettings).first()
    if existing:
        return existing

    settings = models.GlobalSettings()
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
