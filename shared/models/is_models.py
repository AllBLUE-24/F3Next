"""
shared/models/is_models.py

PostgreSQL tables for the Implementation System (IS) — v2 Schema.
Normalised from 4 JSONB-heavy tables to 13 queryable, relational tables.

Tables:
  is_sessions                    — orchestration tracking (slimmed, no JSONB blobs)
  is_files                       — file lifecycle with tri-bucket tracking
  is_file_signals                — WHY a pattern was detected in a file
  is_f3iche_scores               — ALL candidate niche scores (not just the winner)
  is_company_profiles            — versioned company profile snapshots
  is_target_structures           — ERPNext doctype requirements
  is_data_readiness_assessments  — Step 8c gap analysis (data vs target structure)
  is_field_mappings              — column → ERPNext field mappings (one row per mapping)
  is_mapped_data                 — references to R2 extracted/mapped payloads
  is_validation_results          — overall validation status per mapped doctype
  is_validation_errors           — individual queryable errors/warnings
  is_import_plans                — 3-phase import plans
  is_import_logs                 — step-by-step import execution log
  is_audit_trail                 — full history of every action
  is_supervisor_prompts          — exception-driven Supervisor prompts (conversation loop)
"""

from __future__ import annotations

import uuid
from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.sql import func
from shared.database.db import Base
import shared.models.core  # ensure core models are loaded for foreign keys


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ISSession — Orchestration Tracking (slimmed)
# ═══════════════════════════════════════════════════════════════════════════════

class ISSession(Base):
    __tablename__ = "is_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_id = Column(String, nullable=False, unique=True)

    # Status tracking (granular)
    # awaiting_files | scanning_files | infected_halt | parsing_files |
    # inferring_f3iche | awaiting_f3iche_confirmation | verifying_f3iche |
    # building_profile | building_target | mapping_files |
    # validating | awaiting_validation_submission |
    # building_import_plan | awaiting_sandbox_approval |
    # importing_phase_a | importing_phase_b | importing_phase_c |
    # complete | failed
    status = Column(String, nullable=False, default="awaiting_files")

    # Discovery integration (from chatbot)
    discovery_f3iche = Column(String, nullable=True)
    discovery_industry = Column(String, nullable=True)
    discovery_company_size = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_is_sessions_project", "project_id"),
        Index("idx_is_sessions_status", "status"),
        Index("idx_is_sessions_workflow", "workflow_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ISFile — File Lifecycle Tracking
# ═══════════════════════════════════════════════════════════════════════════════

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
    bucket_location = Column(String, nullable=False)
    virus_scan_status = Column(String, nullable=False, default="pending")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_is_files_session", "session_id"),
        Index("idx_is_files_virus_status", "virus_scan_status"),
    )

# ═══════════════════════════════════════════════════════════════════════════════
# 3. ISFileSignal — Signal Detection Details
# ═══════════════════════════════════════════════════════════════════════════════

class ISFileSignal(Base):
    __tablename__ = "is_file_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_files.id", ondelete="CASCADE"),
        nullable=True,  # Some signals are session-level, not file-level
    )

    # Signal details
    # signal_type: file_name | sheet_name | column_header | data_pattern |
    #              row_count | column_count | data_sample
    signal_type = Column(String, nullable=False)
    pattern_matched = Column(String, nullable=False)    # The actual pattern found
    suggests_f3iche = Column(String, nullable=False)    # Which niche this signals
    weight = Column(Float, nullable=False, default=1.0)
    confidence = Column(Float, nullable=True)

    # Context
    found_in = Column(String, nullable=True)            # Sheet name, column index, etc.
    sample_data = Column(Text, nullable=True)           # Sample values (for debugging)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_file_signals_session", "session_id"),
        Index("idx_file_signals_file", "file_id"),
        Index("idx_file_signals_f3iche", "suggests_f3iche"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ISF3icheScore — All Candidate Niche Scores
# ═══════════════════════════════════════════════════════════════════════════════

class ISF3icheScore(Base):
    __tablename__ = "is_f3iche_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Scoring
    f3iche = Column(String, nullable=False)             # Candidate niche
    score = Column(Float, nullable=False)               # 0.0 to 1.0
    confidence = Column(Float, nullable=False)          # LLM confidence

    # Provenance: 'signals' | 'discovery' | 'user'
    source = Column(String, nullable=False)

    # Selection
    is_selected = Column(Boolean, default=False)
    selected_at = Column(DateTime(timezone=True), nullable=True)

    # Verification (after user confirmation)
    user_confirmed = Column(Boolean, default=False)
    # matched | mismatch | pending_clarification
    match_status = Column(String, nullable=True)
    clarification_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_f3iche_scores_session", "session_id"),
        Index("idx_f3iche_scores_selected", "is_selected"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ISCompanyProfile — Versioned Company Profile Snapshots
# ═══════════════════════════════════════════════════════════════════════════════

class ISCompanyProfile(Base):
    __tablename__ = "is_company_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    version = Column(Integer, nullable=False, default=1)

    # Identity
    f3iche = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    industry_sub = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    company_size = Column(String, nullable=True)

    # Discovery comparison
    discovery_alignment_score = Column(Float, nullable=True)
    discovery_mismatches = Column(JSONB, nullable=True)

    # Industry knowledge
    industry_differentiators = Column(JSONB, nullable=True)
    industry_best_practices = Column(JSONB, nullable=True)

    # F3iche-derived config (small, ok for JSONB)
    workflows = Column(JSONB, nullable=True)              # Array of workflow names
    required_modules = Column(JSONB, nullable=True)       # Array of module names
    required_doctypes = Column(JSONB, nullable=True)      # Array of doctype names

    # LLM enrichment
    business_reality = Column(Text, nullable=True)
    context_flags = Column(JSONB, nullable=True)
    data_quality_score = Column(Float, nullable=True)     # 0.0 to 1.0
    completeness_score = Column(Float, nullable=True)     # 0.0 to 1.0
    llm_confidence = Column(Float, nullable=True)         # 0.0 to 1.0

    # R2 reference
    r2_path = Column(String, nullable=True)

    # Metadata
    created_by = Column(String, nullable=True)            # 'system' | 'user'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_company_profiles_session", "session_id"),
        Index("idx_company_profiles_f3iche", "f3iche"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ISTargetStructure — ERPNext Setup Requirements
# ═══════════════════════════════════════════════════════════════════════════════

class ISTargetStructure(Base):
    __tablename__ = "is_target_structures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    f3iche = Column(String, nullable=False)

    # LLM enhancement flag
    llm_enhanced = Column(Boolean, default=False)
    llm_reasoning = Column(Text, nullable=True)

    # Summary counts for quick queries
    total_doctypes = Column(Integer, nullable=True)
    total_setup_steps = Column(Integer, nullable=True)
    total_modules = Column(Integer, nullable=True)

    # Full structure in R2 (too large for DB)
    r2_path = Column(String, nullable=True)

    # Also keep a JSONB copy for easy querying of required_doctypes list
    required_doctypes = Column(JSONB, nullable=True)
    setup_steps = Column(JSONB, nullable=True)
    import_phases = Column(JSONB, nullable=True)
    validation_rules = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_target_structures_session", "session_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ISDataReadinessAssessment — Step 8c Gap Analysis
# ═══════════════════════════════════════════════════════════════════════════════

class ISDataReadinessAssessment(Base):
    __tablename__ = "is_data_readiness_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    ready_doctypes = Column(JSONB, nullable=True)
    partial_doctypes = Column(JSONB, nullable=True)
    missing_doctypes = Column(JSONB, nullable=True)
    unmappable_chunks = Column(JSONB, nullable=True)
    gap_report = Column(JSONB, nullable=True)

    minimum_viable_possible = Column(Boolean, default=True)
    user_action_required = Column(Boolean, default=False)
    questions_for_user = Column(JSONB, nullable=True)
    import_readiness_score = Column(Float, default=1.0)
    executive_summary = Column(Text, nullable=True)
    user_decision = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_data_readiness_session", "session_id"),
        Index("idx_data_readiness_created", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ISFieldMapping — Column → ERPNext Field Mappings
# ═══════════════════════════════════════════════════════════════════════════════

class ISFieldMapping(Base):
    __tablename__ = "is_field_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_files.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Source
    source_filename = Column(String, nullable=False)
    source_sheet_name = Column(String, nullable=True)   # For XLSX files
    source_column = Column(String, nullable=False)
    source_data_type = Column(String, nullable=True)    # string | number | date | boolean

    # Target
    target_doctype = Column(String, nullable=False)
    target_field = Column(String, nullable=False)

    # Mapping metadata
    # exact_match | fuzzy_match | llm_inferred | user_confirmed | historical_match
    mapping_method = Column(String, nullable=False, default="exact_match")
    confidence = Column(Float, nullable=True)

    # User feedback loop
    user_confirmed = Column(Boolean, default=False)
    user_corrected = Column(Boolean, default=False)
    user_correction = Column(JSONB, nullable=True)      # {original_field, corrected_to, reason}

    # Transformation rule
    transformation_rule = Column(String, nullable=True)  # trim | uppercase | date_format etc.

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_field_mappings_session", "session_id"),
        Index("idx_field_mappings_file", "file_id"),
        Index("idx_field_mappings_target", "target_doctype", "target_field"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ISMappedData — References to R2 Extracted/Mapped Payloads
# ═══════════════════════════════════════════════════════════════════════════════

class ISMappedData(Base):
    __tablename__ = "is_mapped_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_files.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Target info
    target_doctype = Column(String, nullable=False)
    source_filename = Column(String, nullable=True)

    # R2 storage (data too large for DB)
    extracted_rows_r2_path = Column(String, nullable=False)
    mapped_payload_r2_path = Column(String, nullable=True)

    # Summary stats
    total_rows = Column(Integer, nullable=True)
    total_mapped_fields = Column(Integer, nullable=True)

    # Validation link
    # pending | validating | passed | failed
    validation_status = Column(String, default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_mapped_data_session", "session_id"),
        Index("idx_mapped_data_doctype", "target_doctype"),
        Index("idx_mapped_data_validation", "validation_status"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ISValidationResult — Overall Validation Status Per Doctype
# ═══════════════════════════════════════════════════════════════════════════════

class ISValidationResult(Base):
    __tablename__ = "is_validation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    mapped_data_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_mapped_data.id", ondelete="CASCADE"),
        nullable=True,
    )

    doctype = Column(String, nullable=False)

    # Overall status: pass | fail | warning
    overall_status = Column(String, nullable=False)

    # R2 reference (full report)
    report_r2_path = Column(String, nullable=True)

    # Summary counts
    total_errors = Column(Integer, default=0)
    total_warnings = Column(Integer, default=0)
    total_records_checked = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_validation_results_session", "session_id"),
        Index("idx_validation_results_status", "overall_status"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 11. ISValidationError — Individual Queryable Errors
# ═══════════════════════════════════════════════════════════════════════════════

class ISValidationError(Base):
    __tablename__ = "is_validation_errors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_validation_results.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Error location
    doctype = Column(String, nullable=False)
    record_index = Column(Integer, nullable=True)       # Row number in file
    field_name = Column(String, nullable=True)

    # Error details
    # missing_required | invalid_type | invalid_format | invalid_value |
    # duplicate | reference_not_found | business_rule_violation
    error_type = Column(String, nullable=False)
    error_message = Column(Text, nullable=False)
    # error | warning
    severity = Column(String, nullable=False)

    # Context
    sample_value = Column(Text, nullable=True)          # The invalid value
    expected_format = Column(Text, nullable=True)       # What was expected

    # Resolution
    auto_fixable = Column(Boolean, default=False)
    suggested_fix = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_validation_errors_result", "validation_result_id"),
        Index("idx_validation_errors_type", "error_type"),
        Index("idx_validation_errors_severity", "severity"),
        Index("idx_validation_errors_doctype", "doctype"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 12. ISImportPlan — 3-Phase Import Plans
# ═══════════════════════════════════════════════════════════════════════════════

class ISImportPlan(Base):
    __tablename__ = "is_import_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Plan metadata
    total_phases = Column(Integer, default=3)
    total_steps = Column(Integer, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)

    # R2 reference (full plan JSON)
    plan_r2_path = Column(String, nullable=True)

    # Plan JSONB (phases array — moderate size, ok for JSONB)
    phases = Column(JSONB, nullable=True)

    # Status: ready | blocked | executing | completed | failed
    status = Column(String, default="ready")
    current_phase = Column(String, nullable=True)       # phase_a | phase_b | phase_c
    current_step = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_import_plans_session", "session_id"),
        Index("idx_import_plans_status", "status"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 13. ISImportLog — Step-by-Step Import Execution Log
# ═══════════════════════════════════════════════════════════════════════════════

class ISImportLog(Base):
    __tablename__ = "is_import_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_import_plans.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Execution details
    phase = Column(String, nullable=False)              # phase_a_config | phase_b_master | phase_c_transactional
    step_number = Column(Integer, nullable=False)
    doctype = Column(String, nullable=False)
    action = Column(String, nullable=False)             # create | update | submit | default_or_skip

    # Result: success | failed | skipped | dry_run
    status = Column(String, nullable=False)
    records_attempted = Column(Integer, default=0)
    records_succeeded = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # Error details (if failed)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)

    # ERPNext response (small, ok for JSONB)
    erpnext_response = Column(JSONB, nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_import_logs_plan", "import_plan_id"),
        Index("idx_import_logs_phase", "phase"),
        Index("idx_import_logs_status", "status"),
        Index("idx_import_logs_doctype", "doctype"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 14. ISAuditTrail — Full History
# ═══════════════════════════════════════════════════════════════════════════════

class ISAuditTrail(Base):
    __tablename__ = "is_audit_trail"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # What happened
    # session_created | file_uploaded | virus_scan_complete | f3iche_inferred |
    # f3iche_confirmed | profile_built | target_generated | mapping_completed |
    # validation_run | import_executed | user_override | error_occurred
    action = Column(String, nullable=False)

    entity_type = Column(String, nullable=True)         # file | mapping | validation | import
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Who did it: user | system | llm | temporal_workflow
    actor = Column(String, nullable=True)

    # Details (small, ok for JSONB)
    details = Column(JSONB, nullable=True)

    # Result: success | failure | partial
    result = Column(String, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_audit_trail_session", "session_id"),
        Index("idx_audit_trail_action", "action"),
        Index("idx_audit_trail_actor", "actor"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 15. ISSupervisorPrompt — Exception-driven user prompts
# ═══════════════════════════════════════════════════════════════════════════════

class ISSupervisorPrompt(Base):
    __tablename__ = "is_supervisor_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("is_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Which step raised this prompt (e.g., mapping, validation, target_structure)
    step = Column(String, nullable=False)

    # open | answered | obsolete
    status = Column(String, nullable=False, default="open")

    # Snapshot of the node status envelope (JSON serializable)
    node_status = Column(JSONB, nullable=True)

    # Supervisor actions (auto_fix / ask_user / hard_block)
    actions = Column(JSONB, nullable=True)

    summary_for_ui = Column(Text, nullable=True)
    answer_payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_is_supervisor_prompts_session", "session_id"),
        Index("idx_is_supervisor_prompts_step", "step"),
        Index("idx_is_supervisor_prompts_status", "status"),
    )

class ISFieldMappingHistory(Base):
    """
    Step 10: Stores conversational corrections so the LLM can learn
    user preferences for future mappings.
    """
    __tablename__ = "is_field_mapping_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("is_sessions.id", ondelete="CASCADE"), nullable=False)
    source_column = Column(String, nullable=False)
    target_doctype = Column(String, nullable=False)
    target_field = Column(String, nullable=False)
    user_confirmed = Column(Boolean, default=True)
    user_corrected = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    