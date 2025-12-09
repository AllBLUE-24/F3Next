# schemas/models/sessions.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

class Session(Base, ReprMixin):
    __tablename__ = "sessions"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    project_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    data = sa.Column(JSONB, nullable=True)
    expires_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    __repr_keys__ = ("id", "project_id")
