"""
shared/models/notification_models.py

Operations control plane — cascade event log and per-recipient notifications.

Tables:
  cascade_events  — one row per ERPNext webhook processed by the cascade layer
  notifications   — one row per recipient delivery (in-app v1; WhatsApp later)

Register in backend/app/main.py alongside other shared models.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from shared.database.db import Base


class CascadeEvent(Base):
    """Audit log for ERPNext events entering the cascade (reactive ops) layer."""

    __tablename__ = "cascade_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    doctype = Column(String, nullable=False)
    doc_name = Column(String, nullable=True)
    trigger_event = Column(String, nullable=False)
    event_payload = Column(JSONB, nullable=True)
    matched_rule_ids = Column(JSONB, nullable=True, default=list)
    risk_tier = Column(String, nullable=False, default="low")
    workflow_id = Column(String, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_cascade_events_project_doctype", "project_id", "doctype"),
    )


class Notification(Base):
    """Per-recipient notification delivery record."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cascade_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cascade_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    recipient_client_id = Column(String, nullable=False, index=True)
    department = Column(String, nullable=True)
    channel = Column(String, nullable=False, default="in_app")
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=True, default=dict)
    risk_tier = Column(String, nullable=False, default="low")
    status = Column(String, nullable=False, default="pending")
    related_os_workflow_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_notifications_project_created", "project_id", "created_at"),
    )
