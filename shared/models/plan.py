"""
shared/models/plan.py

Pydantic models for the ExecutionPlan — the output of the Command Planning Agent
and the primary input to the Payload Generation Agent.

This is the contract between Agent 3 (Planner) and Agent 4 (Payload Generator).
Both agents import from here — never define their own plan shapes.

Plan lifecycle:
  Command Planner builds it → Payload Generator reads steps to build payloads →
  Execution Agent reads steps to make API calls in order →
  Result Formatter reads steps to report what was done.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── PlanStep ─────────────────────────────────────────────────────────────────

class PlanStep(BaseModel):
    """
    A single atomic API call within an ExecutionPlan.

    action:
      create          → POST /api/resource/{doctype}
      submit          → PUT /api/resource/{doctype}/{name}  (workflow transition)
      create_from     → POST /api/resource/{doctype} with data fetched from source doc
      get             → GET  /api/resource/{doctype}/{name}
      update          → PUT  /api/resource/{doctype}/{name}
      cancel          → PUT  /api/resource/{doctype}/{name}  (cancel workflow)
      delete          → DELETE /api/resource/{doctype}/{name}
      search          → GET  /api/resource/{doctype}?filters=...
      report          → GET  /api/method/{report_method}
      bulk_create     → multiple POST calls (async)
      validate_data   → local validation only, no API call
      notify          → POST to notification API

    source_step:
      For create_from steps — which step number's result (doc name) to use
      as the source document. e.g. step 3 "create_from SO" uses result of step 2.

    entities:
      Subset of StructuredIntent.entities relevant to this step.
      Payload Generator uses this to build the API payload for this step.
    """

    step_number:         int
    action:              str                    # see docstring above
    doctype:             str                    # ERPNext doctype name
    depends_on:          Optional[str] = None   # "step_1", "step_2", etc. or None
    rollback_if_failed:  bool          = False

    # For create_from steps
    source_doctype:      Optional[str]       = None
    source_step:         Optional[int]       = None   # step number whose result is the source
    fetch_fields:        list[str]           = Field(default_factory=list)

    # Fields the Payload Generator needs to populate for this step
    required_fields:     list[str]           = Field(default_factory=list)
    optional_fields:     list[str]           = Field(default_factory=list)

    # Entities from StructuredIntent relevant to this step (pre-filtered by Planner)
    entities:            dict[str, Any]      = Field(default_factory=dict)

    # Human-readable notes (for UI and debugging)
    description:         str                 = ""
    rollback_note:       str                 = ""

    # Planner metadata for prerequisite-aware execution
    step_role:           str                 = "main"   # main / prerequisite
    prerequisite_for:    Optional[str]       = None
    resolution_source:   Optional[str]       = None
    payload_template:    dict[str, Any]      = Field(default_factory=dict)


# ─── ExecutionPlan ────────────────────────────────────────────────────────────

class ExecutionPlan(BaseModel):
    """
    The full execution plan for a single user command.

    Single-step plan:  one step, pattern_id=None, is_multi_step=False
    Multi-step plan:   2-6 steps from KB-03 pattern, is_multi_step=True

    risk_level / requires_confirmation:
      Comes from KB-03 pattern definition OR escalated from KB-01 intent risk.
      Confirmation gate in the workflow checks requires_confirmation.

    rollback_strategy:
      "draft_delete"   — draft docs created before failure can be deleted automatically
      "inform_user"    — submitted docs cannot be auto-rolled back; user told which docs remain
      "none"           — read-only / report commands, no rollback needed

    is_async:
      True for bulk operations (bulk_create_items, bulk_sales_orders).
      Workflow handles async differently — queues a background job.
    """

    plan_id:                    str          = Field(default_factory=lambda: str(uuid.uuid4()))
    pattern_id:                 Optional[str] = None   # KB-03 pattern_id or None
    pattern_name:               Optional[str] = None

    steps:                      list[PlanStep] = Field(default_factory=list)

    risk_level:                 str          = "low"   # low / medium / high / critical
    requires_confirmation:      bool         = False
    confirmation_message:       Optional[str] = None

    estimated_api_calls:        int          = 1
    is_multi_step:              bool         = False
    is_async:                   bool         = False   # True for bulk operations

    rollback_strategy:          str          = "none"
    # "draft_delete" / "inform_user" / "none"

    # Template strings from KB-03 (used by Result Formatter)
    success_message_template:   Optional[str] = None
    partial_failure_template:   Optional[str] = None

    def primary_doctype(self) -> str:
        """The main doctype being operated on (from step 1)."""
        if self.steps:
            return self.steps[0].doctype
        return ""

    def all_doctypes(self) -> list[str]:
        """All distinct doctypes touched by this plan."""
        seen: set[str] = set()
        result: list[str] = []
        for step in self.steps:
            if step.doctype and step.doctype not in seen:
                seen.add(step.doctype)
                result.append(step.doctype)
        return result

    def steps_that_rollback(self) -> list[PlanStep]:
        """Steps marked rollback_if_failed=True — created docs to clean up on failure."""
        return [s for s in self.steps if s.rollback_if_failed]