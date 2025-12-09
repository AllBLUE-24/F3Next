# schemas/models/audit_log.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TEXT
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

class AuditLog(Base, ReprMixin):
    __tablename__ = "audit_log"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    entity = sa.Column(sa.Text, nullable=False)
    entity_id = sa.Column(UUID(as_uuid=True), nullable=True)
    action = sa.Column(sa.Text, nullable=False)
    performed_by = sa.Column(sa.Text, nullable=True)
    payload = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    __repr_keys__ = ("id", "entity", "action")