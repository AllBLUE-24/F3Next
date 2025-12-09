# schemas/projects.py
from sqlalchemy import Column, ForeignKey, text, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import TIMESTAMP

from .base import Base
from .mixins import TimestampMixin

# Use the exact enum name that your migrations create.
# (Do NOT let SQLAlchemy auto-create a different unnamed enum.)
PROJECT_STATUS_VALUES = (
    "created",
    "discovery_complete",
    "templates_ready",
    "uploaded",
    "validated",
)

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),  # requires pgcrypto extension (see note)
    )

    client_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    status = Column(
        SAEnum(*PROJECT_STATUS_VALUES, name="project_status"),
        nullable=False,
        server_default=text("'created'"),
    )

    intake_data = Column(JSONB, nullable=True)

    # recommended index on client_id for queries that filter by client
    __table_args__ = (
        Index("ix_projects_client_id", "client_id"),
    )
