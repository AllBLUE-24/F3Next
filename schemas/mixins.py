# schemas/mixins.py
from sqlalchemy import Column, text
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP

class TimestampMixin:
    """Reusable timestamp columns."""
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
        onupdate=func.now(),
    )
