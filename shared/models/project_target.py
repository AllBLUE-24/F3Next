"""
Project-level Target Structure and MVP Boundary Models

These are stored at PROJECT level (not session level) because they depend only on:
- F3iche classification
- Discovery chat context (bottleneck, functional requirements)

They are CORPUS-INDEPENDENT and can be reused across multiple IS runs
if the f3iche and bottleneck remain the same.
"""

from __future__ import annotations

import uuid
from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text, Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from shared.database.db import Base


class ProjectTargetStructure(Base):
    """
    Project-level target structure - generated post-discovery, before file upload.
    Corpus-independent and reusable across IS runs.
    """
    __tablename__ = "project_target_structures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Discovery context
    f3iche = Column(String, nullable=False)
    discovery_bottleneck = Column(Text, nullable=True)  # Primary pain point
    
    # LLM enhancement flag
    llm_enhanced = Column(Boolean, default=False)
    llm_reasoning = Column(Text, nullable=True)

    # Summary counts
    total_doctypes = Column(Integer, nullable=True)
    total_seed_doctypes = Column(Integer, nullable=True)
    total_setup_steps = Column(Integer, nullable=True)

    # Full structure in R2
    r2_target_path = Column(String, nullable=True)  # target_structure.json
    r2_mvp_path = Column(String, nullable=True)     # mvp_boundary.json

    # JSONB for easy querying
    seed_doctypes = Column(JSONB, nullable=True)      # MVP seed doctypes
    required_doctypes = Column(JSONB, nullable=True)  # All doctypes (seeds + prereqs)
    setup_steps = Column(JSONB, nullable=True)        # Ordered setup actions
    import_phases = Column(JSONB, nullable=True)      # Phase groupings
    validation_rules = Column(JSONB, nullable=True)   # F3iche-specific rules
    
    # MVP boundary
    mvp_focus = Column(JSONB, nullable=True)          # From discovery
    deferred_doctypes = Column(JSONB, nullable=True)  # Empty for post-discovery
    
    # Flags
    corpus_independent = Column(Boolean, default=True)
    graph_driven = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProjectMVPBoundary(Base):
    """
    Project-level MVP boundary - separate from target structure for clarity.
    Defines what's in scope for the MVP implementation.
    """
    __tablename__ = "project_mvp_boundaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One MVP boundary per project
        index=True,
    )

    # MVP definition
    f3iche = Column(String, nullable=False)
    primary_bottleneck = Column(Text, nullable=True)
    functional_requirements = Column(JSONB, nullable=True)  # List of strings
    
    # Scope
    seed_doctypes = Column(JSONB, nullable=True)           # What's in MVP
    deferred_doctypes = Column(JSONB, nullable=True)       # What's deferred
    
    # Mode flags
    mode = Column(String, nullable=False, default="f3iche_template")  # or "mvp_translation"
    llm_enhanced = Column(Boolean, default=False)
    llm_reasoning = Column(Text, nullable=True)
    
    # R2 storage
    r2_path = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
