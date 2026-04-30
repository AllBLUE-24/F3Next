"""
shared/models/cvs_models.py

PostgreSQL tables for the Context Versioning Service (CVS).
Uses the same Base and engine from shared.database.db.

Tables (2):
  context_snapshots — versioned context layers per company (identity / master_data / transaction_intel)
  context_events    — raw event audit log (ERPNext webhooks + OS command triggers)

Relationships:
  projects ──< context_snapshots
  projects ──< context_events

Register in main.py (already imported via _all_models expansion):
  from shared.models.cvs_models import ContextSnapshot, ContextEvent
"""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from shared.database.db import Base


# ─── Table 1: ContextSnapshot ─────────────────────────────────────────────────

class ContextSnapshot(Base):
    """
    One row per versioned context layer per company.

    layer values:
      "identity"         — company profile, ERP credentials, static config (set once at IS completion)
      "master_data"      — live registry of customers, suppliers, items, warehouses (updates on change)
      "transaction_intel"— rolling 30/90-day business activity summary (daily or on-demand rebuild)

    version — monotonically increasing integer per (project_id, layer).
    The OS always reads the MAX(version) row for a given project_id + layer.

    data — the full JSON payload for this layer. No credentials in master_data or transaction_intel.
    Credentials are ONLY in the identity layer, and even there only used server-side.

    trigger_event — what caused this version to be written:
      "force_sync"       — IS pipeline called /api/cvs/force-sync after deployment
      "webhook"          — an ERPNext webhook arrived and triggered a rebuild
      "os_command"       — an OS command succeeded (optimistic context_event log entry)
      "scheduled"        — nightly full-sync (Phase 3)

    r2_key — the R2 object key where the full payload is also stored.
    Supabase holds the payload for fast indexed queries; R2 holds it for analytics + large payloads.
    """

    __tablename__ = "context_snapshots"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id      = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        # NOTE: The FK to projects.id is enforced at the database level in Supabase.
        # We do NOT declare ForeignKey() here because the cvs_worker only loads CVS
        # models and SQLAlchemy cannot resolve references to tables it has never imported.
        # Declaring it here crashes with NoReferencedTableError on the first DB write.
    )

    # Which context layer this row holds
    layer           = Column(String, nullable=False)   # identity / master_data / transaction_intel

    # Monotonically increasing version per (project_id, layer)
    version         = Column(Integer, nullable=False, default=1)

    # The full context payload
    data            = Column(JSONB, nullable=False, default=dict)

    # What triggered this snapshot
    trigger_event   = Column(String, nullable=False, default="force_sync")
    # force_sync / webhook / os_command / scheduled

    # For webhook triggers — which ERPNext doctype caused the rebuild
    trigger_doctype = Column(String, nullable=True)   # e.g. "Sales Order", "Customer"

    # R2 object key for full payload (analytics + large snapshots)
    r2_key          = Column(String, nullable=True)
    # e.g. "context/{company_slug}/master_data/v00042.json"

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_cvs_snapshots_project_layer", "project_id", "layer"),
        Index("idx_cvs_snapshots_project_version", "project_id", "layer", "version"),
    )

    def __repr__(self) -> str:
        return (
            f"<ContextSnapshot(project={self.project_id}, "
            f"layer={self.layer}, v={self.version}, trigger={self.trigger_event})>"
        )


# ─── Table 2: ContextEvent ────────────────────────────────────────────────────

class ContextEvent(Base):
    """
    Raw event audit log — every event that touched the context store.

    event_type — semantic label for the event, e.g.:
      "customer_created", "so_submitted", "stock_updated",
      "os_command_success", "force_sync_triggered"

    event_payload — the raw webhook body or the OS command summary that triggered this.

    version_produced — which ContextSnapshot version this event produced (null if no
      snapshot was written, e.g. a duplicate webhook that didn't change anything).

    processed_at — when the CVS finished processing this event. Null means still in flight
      (Temporal workflow is running). Used to detect stuck events.
    """

    __tablename__ = "context_events"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id       = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        # NOTE: Same as ContextSnapshot — DB-level FK enforced in Supabase.
        # Not declared here to avoid NoReferencedTableError in cvs_worker.
    )

    event_type       = Column(String, nullable=False)
    event_payload    = Column(JSONB, nullable=True)

    # Which ERPNext doctype this event relates to (for webhook events)
    doctype          = Column(String, nullable=True)
    doc_name         = Column(String, nullable=True)   # e.g. "SO-00241"

    # Link back to the snapshot that was produced (null if not yet processed)
    version_produced = Column(Integer, nullable=True)

    # Temporal workflow ID that is processing this event (for deduplication)
    workflow_id      = Column(String, nullable=True)

    received_at      = Column(DateTime(timezone=True), server_default=func.now())
    processed_at     = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_cvs_events_project", "project_id"),
        Index("idx_cvs_events_type",    "project_id", "event_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<ContextEvent(project={self.project_id}, "
            f"event={self.event_type}, doctype={self.doctype}, doc={self.doc_name})>"
        )
