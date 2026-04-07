"""
shared/models/is_models.py

PostgreSQL tables for the Implementation System (IS).
Offloads Temporal execution state completely into scalable JSONB models, eradicating memory bloat.

New tables:
  is_sessions    — one per implementation attempt for a project. Stores profile/target structure.
  is_files       — tracks all R2 bucket file uploads with their strict tri-bucket virus scan states.
  is_mappings    — captures intermediate AI schema mapping for easy UI rewinds.
  is_import_runs — tracks the final execution payload and ERPNext responses.
"""

from __future__ import annotations

import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from shared.database.db import Base
import shared.models.core  # ensure core models are loaded for foreign keys


class ISSession(Base):
    __tablename__ = "is_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_id = Column(String, nullable=False, unique=True)
    
    status = Column(String, nullable=False, default="awaiting_files") 
    
    # Core state
    f3iche_profile = Column(JSONB, nullable=True)     # Stores industry inferences, confidence
    target_structure = Column(JSONB, nullable=True)   # Resolved doctypes from Target Agent

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_is_sessions_project", "project_id"),
        Index("idx_is_sessions_workflow", "workflow_id"),
    )


class ISFile(Base):
    __tablename__ = "is_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    original_filename = Column(String, nullable=False)
    r2_object_key = Column(String, nullable=False)
    bucket_location = Column(String, nullable=False, default="quarantine-data")
    
    # Virus scanning pipeline state
    virus_scan_status = Column(String, nullable=False, default="pending") 
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class ISMapping(Base):
    __tablename__ = "is_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    doctype_name = Column(String, nullable=False)
    
    # Massive JSON outputs from the Mapping/Validation Agents
    extracted_rows = Column(JSONB, nullable=True)
    field_mapping = Column(JSONB, nullable=True)
    validation_report = Column(JSONB, nullable=True)
    
    status = Column(String, nullable=False, default="draft") # draft -> validated

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_is_mappings_session", "session_id"),
    )


class ISImportRun(Base):
    __tablename__ = "is_import_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    phase = Column(String, nullable=False) 
    execution_plan = Column(JSONB, nullable=False)
    results = Column(JSONB, nullable=True)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
