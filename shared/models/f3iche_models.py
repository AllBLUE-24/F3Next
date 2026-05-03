"""F3iche definitions stored in Postgres (hot-reloadable Tier 2)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from shared.database.db import Base


class F3icheDefinition(Base):
    """
    Industry addendum (Tier 2). `source` is bundled | custom.
    """

    __tablename__ = "f3iche_definitions"

    f3iche_id = Column(String(128), primary_key=True)
    version = Column(Integer, nullable=False, default=1)
    source = Column(String(32), nullable=False, default="custom")
    definition = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
