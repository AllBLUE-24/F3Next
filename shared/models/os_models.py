"""
shared/database/os_models.py

PostgreSQL tables for the ERP Operating System.
Uses the same Base and engine from shared.database.db — no new DB connection.

New tables (3):
  os_sessions       — one per terminal session, holds rolling conversation context
  os_commands       — one per NL command, full pipeline audit trail
  os_clarifications — one per clarification Q&A round within a command

Relationships:
  projects ──< os_sessions ──< os_commands ──< os_clarifications
  clients  ──< os_sessions

Register in Alembic env.py:
  from shared.database.os_models import OSSession, OSCommand, OSClarification
  and add to target_metadata.

Then run:
  alembic revision --autogenerate -m "add_os_tables"
  alembic upgrade head
"""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from shared.database.db import Base


# ─── Table 1: OSSession ───────────────────────────────────────────────────────

class OSSession(Base):
    """
    One row per OS terminal session.
    A session groups multiple commands under shared conversation context.

    session_context — rolling window of last N turns (max 6), updated after each command
      Format: [{"role": "user"|"assistant", "content": str}, ...]
      Sent to Clarity Agent for pronoun/reference resolution ("the same customer",
      "add 50 more", "that order").

    company_context — KB-12 style profile, cached once at session start
      Contains: ERP URL, API credentials, default warehouse/company/currency/price_list,
      enabled modules, fiscal year, country.
      Refreshed if >1 hour old (checked in company_profile.py).
      This is the SOURCE for all downstream agents — they never re-query projects table.
    """

    __tablename__ = "os_sessions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id      = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id       = Column(String, ForeignKey("clients.id"), nullable=False)

    status          = Column(String, nullable=False, default="active")   # active / ended
    erp_type        = Column(String, nullable=False, default="erpnext")

    # Rolling conversation — last 6 turns max, appended after each command
    session_context = Column(JSONB, nullable=False, default=list)

    # Cached company profile — see company_profile.py for full shape
    company_context = Column(JSONB, nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    last_active     = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    ended_at        = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_os_sessions_project", "project_id"),
        Index("idx_os_sessions_client",  "client_id"),
    )

    def __repr__(self) -> str:
        return f"<OSSession(id={self.id}, project={self.project_id}, status={self.status})>"


# ─── Table 2: OSCommand ───────────────────────────────────────────────────────

class OSCommand(Base):
    """
    One row per NL command. Complete pipeline audit trail.

    Each agent writes its output into the relevant JSONB column as it finishes:
      Clarity Agent      → intent           (StructuredIntent dict)
      Context Retrieval  → context_snapshot (subset of context bundle, NO credentials)
      Command Planner    → plan             (ExecutionPlan)
      Payload Generator  → payload          (final ERPNext API payload)
      Validation Agent   → validation       (ValidationResult)
      Execution Agent    → erp_response     (raw ERPNext API response)
      Result Formatter   → formatted_response (human-readable Text)

    workflow_id — links this row to the live Temporal workflow execution.
    Used by os_launcher.py for status polling and signal sending.

    erp_doc_* — filled after successful execution.
    Gives the frontend a direct "Open in ERPNext" deep-link.
    """

    __tablename__ = "os_commands"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id          = Column(
        UUID(as_uuid=True),
        ForeignKey("os_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id          = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    client_id           = Column(String, ForeignKey("clients.id"), nullable=False)

    # Temporal workflow handle — unique per command
    workflow_id         = Column(String, nullable=False, unique=True)

    # What the user typed
    raw_prompt          = Column(Text, nullable=False)

    # Progressive pipeline outputs (each agent writes its own column)
    intent              = Column(JSONB, nullable=True)
    context_snapshot    = Column(JSONB, nullable=True)   # No credentials — safe to log
    plan                = Column(JSONB, nullable=True)
    payload             = Column(JSONB, nullable=True)
    validation          = Column(JSONB, nullable=True)
    erp_response        = Column(JSONB, nullable=True)
    formatted_response  = Column(Text,  nullable=True)

    # Status — updated by workflow signals via os_launcher
    status              = Column(String, nullable=False, default="pending")
    # pending → processing → done / error / cancelled
    risk_level          = Column(String, nullable=False, default="low")

    # ERPNext document reference (filled on success — enables UI deep-link)
    erp_doc_name        = Column(String, nullable=True)   # e.g. "SO-00234"
    erp_doc_type        = Column(String, nullable=True)   # e.g. "Sales Order"
    erp_doc_link        = Column(String, nullable=True)   # Full ERPNext URL

    # Timing
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    completed_at        = Column(DateTime(timezone=True), nullable=True)
    duration_ms         = Column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_os_commands_session",  "session_id"),
        Index("idx_os_commands_project",  "project_id"),
        # Hot path: every status poll hits this index
        Index("idx_os_commands_workflow", "workflow_id"),
    )

    def __repr__(self) -> str:
        intent_id = self.intent.get("intent_id") if self.intent else None
        return f"<OSCommand(id={self.id}, intent={intent_id}, status={self.status})>"


# ─── Table 3: OSClarification ─────────────────────────────────────────────────

class OSClarification(Base):
    """
    One row per clarification round within a command (max 3 rounds).

    Kept separate from OSCommand for product analytics:
      — Which intents trigger the most clarifications?
      — What is the average answer latency?
      — Which clarification questions most often need rephrasing?

    answered_at is null while the Temporal workflow is paused waiting for the
    user's answer signal. Set when the /answer endpoint receives the answer.
    """

    __tablename__ = "os_clarifications"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    command_id   = Column(
        UUID(as_uuid=True),
        ForeignKey("os_commands.id", ondelete="CASCADE"),
        nullable=False,
    )

    round_number = Column(Integer, nullable=False, default=1)
    question     = Column(Text, nullable=False)     # What the Clarity Agent asked
    answer       = Column(Text, nullable=True)      # null until the user answers

    asked_at     = Column(DateTime(timezone=True), server_default=func.now())
    answered_at  = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_os_clarif_command", "command_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<OSClarification(command={self.command_id}, "
            f"round={self.round_number}, answered={self.answered_at is not None})>"
        )