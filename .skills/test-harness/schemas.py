"""Pydantic models for test harness scenarios and results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================================
# Scenario Models
# ============================================================================


class CompanyContext(BaseModel):
    """Company context for test scenario."""

    name: str = Field(description="Company name")
    industry: str = Field(description="Industry sector")
    size: Literal["micro", "small", "medium"] = Field(
        description="Company size (MSME classification)"
    )
    f3iche: str = Field(description="F3iche archetype path (e.g., manufacturing/project/chemical)")
    location: str = Field(default="India", description="Geographic location")


class ExpectedMVP(BaseModel):
    """Expected MVP boundary for test scenario."""

    seed_doctypes: list[str] = Field(
        description="Day-1 required doctypes (must_create)"
    )
    deferred_doctypes: list[str] = Field(
        default_factory=list,
        description="Post-MVP doctypes (optional_if_absent)",
    )
    dependency_graph: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Doctype dependencies (key depends on values)",
    )


class CorpusFileStub(BaseModel):
    """Corpus file template for simulated user to generate."""

    filename: str = Field(description="File name (e.g., items.csv)")
    expected_doctype: str = Field(description="Expected doctype assignment")
    required_columns: list[str] = Field(
        default_factory=list,
        description="Columns that must be present",
    )
    sample_row_count: int = Field(
        default=10, ge=1, description="Number of sample rows to generate"
    )
    field_coverage_percent: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="% of required fields present",
    )


class GapResponseTemplate(BaseModel):
    """Template for simulated user to respond to data gap questions."""

    gap_field: str = Field(description="Field name causing gap")
    doctype: str = Field(description="Doctype context")
    response_type: Literal["provide_value", "defer", "skip"] = Field(
        description="How to respond to gap"
    )
    value: str | None = Field(
        default=None, description="Value to provide if response_type=provide_value"
    )


class TestScenario(BaseModel):
    """Complete test scenario definition."""

    name: str = Field(description="Unique scenario name (kebab-case)")
    description: str = Field(description="What this scenario tests")
    context: CompanyContext = Field(description="Company context")
    pain_point: str = Field(
        description="Bottleneck description for discovery chat"
    )
    expected_mvp: ExpectedMVP = Field(description="Expected MVP boundary")
    corpus_files: list[CorpusFileStub] = Field(
        description="Corpus files to generate/upload"
    )
    gap_responses: list[GapResponseTemplate] = Field(
        default_factory=list, description="How to respond to data gaps"
    )
    expected_validation_issues: list[str] = Field(
        default_factory=list,
        description="Expected validation errors (if any)",
    )
    expected_record_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Expected ERPNext record counts by doctype",
    )


# ============================================================================
# Oracle Models
# ============================================================================


class OracleStage(str, Enum):
    """Pipeline stages validated by oracles."""

    DISCOVERY = "discovery"
    CORPUS = "corpus"
    READINESS = "readiness"
    MAPPING = "mapping"
    VALIDATION = "validation"
    IMPORT = "import"


class OracleDiff(BaseModel):
    """Diff between expected and actual for an oracle check."""

    expected: Any = Field(description="Expected value")
    actual: Any = Field(description="Actual value")
    diff_type: Literal["missing", "extra", "mismatch", "structure"] = Field(
        description="Type of difference"
    )
    details: str = Field(description="Human-readable diff explanation")


class StageOracleResult(BaseModel):
    """Oracle result for a single pipeline stage."""

    stage: OracleStage
    passed: bool
    diffs: list[OracleDiff] = Field(default_factory=list)
    score: float = Field(
        ge=0.0, le=1.0, description="Similarity score (1.0 = perfect match)"
    )
    message: str = Field(description="Summary message")


class OracleReport(BaseModel):
    """Complete oracle validation report."""

    scenario_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    stage_results: list[StageOracleResult]
    all_passed: bool = Field(description="True if all stages passed")
    first_failure_stage: OracleStage | None = Field(
        default=None, description="First stage that failed (if any)"
    )
    overall_score: float = Field(
        ge=0.0, le=1.0, description="Average score across stages"
    )


# ============================================================================
# Diagnostician Models
# ============================================================================


class F3NextLayer(str, Enum):
    """F3Next architecture layers (from FOUNDATIONS.md)."""

    L0_LLM = "L0"  # LLM prompt/router
    L1_BOUNDARY = "L1"  # Discovery boundary logic
    L2_CORPUS = "L2"  # Corpus understanding
    L3_READINESS = "L3"  # Readiness assessment
    L4_MAPPING = "L4"  # Mapping logic
    L5_VALIDATION = "L5"  # Validation logic
    L6_IMPORT = "L6"  # Import execution


class FixType(str, Enum):
    """Types of fixes diagnostician can propose."""

    STRUCTURAL = "structural"  # Code change (preferred)
    KB_PROMOTION = "kb_promotion"  # F3iche KB override
    PATCH = "patch"  # Hardcoded workaround (last resort)
    PROMPT_REFINEMENT = "prompt_refinement"  # L0 prompt update


class ProposedChange(BaseModel):
    """A single proposed code/config change."""

    file_path: str = Field(description="Relative path to file to change")
    change_type: Literal["edit", "create", "delete"] = Field(
        description="Type of change"
    )
    description: str = Field(description="What this change does")
    diff_preview: str | None = Field(
        default=None, description="Expected diff (for edits)"
    )
    rationale: str = Field(description="Why this change fixes the issue")


class DiagnosticReport(BaseModel):
    """Diagnostician analysis and fix proposal."""

    scenario_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    failed_stage: OracleStage
    layer: F3NextLayer
    fix_type: FixType
    root_cause: str = Field(description="Plain-language root cause explanation")
    proposed_changes: list[ProposedChange]
    confidence: Literal["high", "medium", "low"] = Field(
        description="Diagnostician confidence in proposed fix"
    )
    test_coverage: list[str] = Field(
        default_factory=list,
        description="Test files to add/update for regression coverage",
    )
    verification_steps: list[str] = Field(
        default_factory=list,
        description="How to verify fix worked",
    )


# ============================================================================
# Test Result Models
# ============================================================================


class TestStatus(str, Enum):
    """Test execution status."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"  # Test harness error (not scenario failure)
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class TestResult(BaseModel):
    """Final test execution result."""

    scenario_name: str
    status: TestStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float
    oracle_report: OracleReport | None = Field(
        default=None, description="Oracle validation results"
    )
    diagnostic_report: DiagnosticReport | None = Field(
        default=None, description="Diagnostician analysis (if failed)"
    )
    error_message: str | None = Field(
        default=None, description="Error details (if status=error)"
    )
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Paths to saved artifacts (logs, diffs, etc.)",
    )
    fixed_by_iteration: int | None = Field(
        default=None,
        description="Which iteration fixed the issue (if auto-implement enabled)",
    )


class TestSuiteResult(BaseModel):
    """Result of running multiple scenarios."""

    suite_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_scenarios: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_seconds: float
    results: list[TestResult]
    coverage_matrix: dict[str, dict[OracleStage, bool]] = Field(
        default_factory=dict,
        description="Scenario x stage pass/fail matrix",
    )
