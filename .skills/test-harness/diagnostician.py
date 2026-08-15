"""Diagnostician for triaging test failures and proposing fixes."""

from __future__ import annotations

from datetime import datetime

from .schemas import (
    DiagnosticReport,
    F3NextLayer,
    FixType,
    OracleDiff,
    OracleReport,
    OracleStage,
    ProposedChange,
    TestScenario,
)


class Diagnostician:
    """Analyzes oracle failures and proposes targeted fixes."""

    def diagnose(
        self, oracle_report: OracleReport, scenario: TestScenario
    ) -> DiagnosticReport:
        """Triage oracle failure and generate fix proposal.
        
        Args:
            oracle_report: Oracle validation results
            scenario: Test scenario that failed
        
        Returns:
            Diagnostic report with proposed fixes
        """
        failed_stage = oracle_report.first_failure_stage
        if failed_stage is None:
            raise ValueError("Cannot diagnose passing test")

        # Get diffs for failed stage
        stage_result = next(
            r for r in oracle_report.stage_results if r.stage == failed_stage
        )
        diffs = stage_result.diffs

        # Classify by layer
        layer = self._classify_layer(failed_stage, diffs)

        # Determine fix type
        fix_type = self._determine_fix_type(layer, diffs)

        # Generate root cause
        root_cause = self._explain_root_cause(failed_stage, diffs, scenario)

        # Propose changes
        proposed_changes = self._propose_changes(layer, fix_type, failed_stage, diffs)

        # Test coverage
        test_coverage = self._recommend_test_coverage(layer, failed_stage)

        # Verification steps
        verification_steps = self._generate_verification_steps(failed_stage)

        # Confidence
        confidence = self._assess_confidence(diffs, layer)

        return DiagnosticReport(
            scenario_name=scenario.name,
            timestamp=datetime.utcnow(),
            failed_stage=failed_stage,
            layer=layer,
            fix_type=fix_type,
            root_cause=root_cause,
            proposed_changes=proposed_changes,
            confidence=confidence,
            test_coverage=test_coverage,
            verification_steps=verification_steps,
        )

    def _classify_layer(
        self, stage: OracleStage, diffs: list[OracleDiff]
    ) -> F3NextLayer:
        """Classify failure by F3Next architecture layer.
        
        Args:
            stage: Pipeline stage that failed
            diffs: Differences from oracle
        
        Returns:
            Identified layer
        """
        if stage == OracleStage.DISCOVERY:
            # Discovery failures could be L0 (LLM) or L1 (boundary logic)
            # Heuristic: if MVP is completely wrong, L0; if deps missing, L1
            if any(d.diff_type == "structure" for d in diffs):
                return F3NextLayer.L0_LLM
            else:
                return F3NextLayer.L1_BOUNDARY
        elif stage == OracleStage.CORPUS:
            return F3NextLayer.L2_CORPUS
        elif stage == OracleStage.READINESS:
            return F3NextLayer.L3_READINESS
        elif stage == OracleStage.MAPPING:
            return F3NextLayer.L4_MAPPING
        elif stage == OracleStage.VALIDATION:
            return F3NextLayer.L5_VALIDATION
        elif stage == OracleStage.IMPORT:
            return F3NextLayer.L6_IMPORT
        else:
            return F3NextLayer.L1_BOUNDARY  # Default

    def _determine_fix_type(
        self, layer: F3NextLayer, diffs: list[OracleDiff]
    ) -> FixType:
        """Determine appropriate fix type for layer.
        
        Args:
            layer: Identified layer
            diffs: Differences from oracle
        
        Returns:
            Fix type
        """
        if layer == F3NextLayer.L0_LLM:
            return FixType.PROMPT_REFINEMENT
        elif layer in [
            F3NextLayer.L1_BOUNDARY,
            F3NextLayer.L3_READINESS,
            F3NextLayer.L4_MAPPING,
            F3NextLayer.L5_VALIDATION,
            F3NextLayer.L6_IMPORT,
        ]:
            return FixType.STRUCTURAL
        elif layer == F3NextLayer.L2_CORPUS:
            # Corpus failures might be KB promotion if archetype-specific
            if len(diffs) == 1:
                return FixType.KB_PROMOTION
            else:
                return FixType.STRUCTURAL
        else:
            return FixType.STRUCTURAL

    def _explain_root_cause(
        self,
        stage: OracleStage,
        diffs: list[OracleDiff],
        scenario: TestScenario,
    ) -> str:
        """Generate plain-language root cause explanation.
        
        Args:
            stage: Failed stage
            diffs: Oracle diffs
            scenario: Test scenario
        
        Returns:
            Root cause explanation
        """
        if stage == OracleStage.DISCOVERY:
            if any("Missing seed doctypes" in d.details for d in diffs):
                missing = [
                    d.details.split(": ")[1]
                    for d in diffs
                    if "Missing seed doctypes" in d.details
                ]
                return f"Discovery did not include expected seed doctypes: {missing}. Likely cause: MVP inference from pain point '{scenario.pain_point}' failed to identify necessary doctypes."
            elif any("Unexpected seed doctypes" in d.details for d in diffs):
                extra = [
                    d.details.split(": ")[1]
                    for d in diffs
                    if "Unexpected seed doctypes" in d.details
                ]
                return f"Discovery included unexpected seed doctypes: {extra}. Likely cause: Scope creep in target boundary generation or incorrect transitive dependency classification."
        elif stage == OracleStage.CORPUS:
            return f"Corpus file-doctype assignments did not match expected. {len(diffs)} file(s) misclassified. Likely cause: LLM corpus understanding or filename prior overrides canonical assignment."
        elif stage == OracleStage.READINESS:
            return f"Readiness assessment viability mismatch. Likely cause: Gap analysis logic or default fail-closed contract issue."
        elif stage == OracleStage.MAPPING:
            return f"Mapping produced {diffs[0].actual} files instead of {diffs[0].expected}. Likely cause: Candidate doctype restriction or mapping routing logic."
        elif stage == OracleStage.VALIDATION:
            return f"Validation error count mismatch. Likely cause: Required field resolution or validation predicate logic."
        elif stage == OracleStage.IMPORT:
            return f"Import record counts did not match expected. Likely cause: ERPNext API error or import phase execution issue."

        return f"Unknown root cause for {stage} failure."

    def _propose_changes(
        self,
        layer: F3NextLayer,
        fix_type: FixType,
        stage: OracleStage,
        diffs: list[OracleDiff],
    ) -> list[ProposedChange]:
        """Generate specific code/config changes.
        
        Args:
            layer: Identified layer
            fix_type: Fix type
            stage: Failed stage
            diffs: Oracle diffs
        
        Returns:
            List of proposed changes
        """
        changes = []

        if layer == F3NextLayer.L0_LLM:
            changes.append(
                ProposedChange(
                    file_path="shared/llm/prompts/discovery_planner.py",
                    change_type="edit",
                    description="Refine MVP inference prompt to better detect seed doctypes from pain point",
                    rationale="L0 prompt needs to explicitly ask LLM to identify transitive dependencies for pain point",
                )
            )
        elif layer == F3NextLayer.L1_BOUNDARY:
            changes.append(
                ProposedChange(
                    file_path="containers/discovery/target/build_target.py",
                    change_type="edit",
                    description="Update _classify_against_baseline to ensure transitive deps are must_create",
                    rationale="Discovery is missing required dependencies for seed doctypes",
                )
            )
        elif layer == F3NextLayer.L2_CORPUS:
            changes.append(
                ProposedChange(
                    file_path="containers/implementation/mapping_agent/activities.py",
                    change_type="edit",
                    description="Ensure canonical corpus assignments override filename priors",
                    rationale="Corpus assignments should be authoritative source for file-doctype mapping",
                )
            )
        elif layer == F3NextLayer.L3_READINESS:
            changes.append(
                ProposedChange(
                    file_path="containers/implementation/data_readiness_agent/activities.py",
                    change_type="edit",
                    description="Fix gap analysis logic to correctly identify missing required fields",
                    rationale="Readiness viability assessment is incorrect",
                )
            )
        elif layer == F3NextLayer.L4_MAPPING:
            changes.append(
                ProposedChange(
                    file_path="containers/implementation/mapping_agent/activities.py",
                    change_type="edit",
                    description="Fix _get_candidate_doctypes to respect confirmed target scope",
                    rationale="Mapping is operating outside confirmed MVP boundary",
                )
            )
        elif layer == F3NextLayer.L5_VALIDATION:
            changes.append(
                ProposedChange(
                    file_path="containers/implementation/validation_agent/activities.py",
                    change_type="edit",
                    description="Fix required field resolution to use unified resolve_required_fields",
                    rationale="Validation is using different required field source than readiness",
                )
            )
        elif layer == F3NextLayer.L6_IMPORT:
            changes.append(
                ProposedChange(
                    file_path="containers/implementation/import_agent/activities.py",
                    change_type="edit",
                    description="Add retry logic for ERPNext API errors",
                    rationale="Import phase failed due to transient API error",
                )
            )

        return changes

    def _recommend_test_coverage(
        self, layer: F3NextLayer, stage: OracleStage
    ) -> list[str]:
        """Recommend test files to add/update.
        
        Args:
            layer: Identified layer
            stage: Failed stage
        
        Returns:
            List of test file paths
        """
        if stage == OracleStage.DISCOVERY:
            return ["containers/discovery/target/tests/test_build_target.py"]
        elif stage == OracleStage.CORPUS:
            return ["containers/implementation/tests/test_corpus_assignments.py"]
        elif stage == OracleStage.READINESS:
            return ["containers/implementation/tests/test_readiness_contracts.py"]
        elif stage == OracleStage.MAPPING:
            return ["containers/implementation/tests/test_mapping_routing.py"]
        elif stage == OracleStage.VALIDATION:
            return ["containers/implementation/tests/test_validation_engine.py"]
        elif stage == OracleStage.IMPORT:
            return ["containers/implementation/tests/test_import_plan.py"]
        else:
            return []

    def _generate_verification_steps(self, stage: OracleStage) -> list[str]:
        """Generate verification steps for fix.
        
        Args:
            stage: Failed stage
        
        Returns:
            List of verification steps
        """
        base_steps = [
            f"Re-run test scenario to verify {stage} oracle passes",
            "Run full regression suite: pytest containers/",
            "Check docs/plans/is-pipeline-coherence.md acceptance criteria",
        ]

        if stage == OracleStage.DISCOVERY:
            base_steps.insert(
                1, "Verify MVP boundary includes all expected seed doctypes"
            )
        elif stage == OracleStage.CORPUS:
            base_steps.insert(
                1, "Verify corpus assignments match expected file-doctype mappings"
            )

        return base_steps

    def _assess_confidence(
        self, diffs: list[OracleDiff], layer: F3NextLayer
    ) -> str:
        """Assess diagnostician confidence in proposed fix.
        
        Args:
            diffs: Oracle diffs
            layer: Identified layer
        
        Returns:
            Confidence level: "high", "medium", "low"
        """
        # Heuristic: fewer diffs + structural fix = higher confidence
        if len(diffs) == 1 and layer != F3NextLayer.L0_LLM:
            return "high"
        elif len(diffs) <= 3:
            return "medium"
        else:
            return "low"
