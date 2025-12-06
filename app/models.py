# app/models.py
from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class FilterMode(str, enum.Enum):
    strict = "strict"
    moderate = "moderate"
    relaxed = "relaxed"


class ResultType(str, enum.Enum):
    text = "text"
    image = "image"
    video = "video"


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(512), nullable=False)
    filter_mode = Column(Enum(FilterMode), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    total_results = Column(Integer, default=0)
    safe_results = Column(Integer, default=0)
    blocked_results = Column(Integer, default=0)

    results = relationship(
        "SearchResult",
        back_populates="search_query",
        cascade="all, delete-orphan",
    )


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("search_queries.id", ondelete="CASCADE"))
    title = Column(String(512), nullable=False)
    url = Column(String(1024), nullable=False)
    snippet = Column(Text, nullable=False)

    type = Column(Enum(ResultType), default=ResultType.text, nullable=False)
    is_blocked = Column(Boolean, default=False)
    blocked_reason = Column(String(256), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    search_query = relationship("SearchQuery", back_populates="results")


class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id = Column(Integer, primary_key=True, index=True)
    # OLD:
    # filter_mode = Column(Enum(FilterMode), default=FilterMode.strict, nullable=False)
    # NEW:
    filter_mode = Column(Enum(FilterMode), default=FilterMode.relaxed, nullable=False)

    parental_controls = Column(Boolean, default=True)
    notifications = Column(Boolean, default=True)
    save_search_history = Column(Boolean, default=True)

    # comma-separated lists
    blocked_keywords = Column(Text, default="")
    allowed_domains = Column(Text, default="")

