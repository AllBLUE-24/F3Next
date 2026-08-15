"""Oracles for validating pipeline outputs against expected states."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .schemas import (
    OracleDiff,
    OracleReport,
    OracleStage,
    StageOracleResult,
    TestScenario,
)


class Oracle:
    """Validates pipeline outputs against scenario expectations."""

    def __init__(self, scenario: TestScenario):
        """Initialize oracle with test scenario.
        
        Args:
            scenario: Test scenario defining expectations
        """
        self.scenario = scenario

    def validate_all(
        self,
        discovery_result: dict[str, Any],
        corpus_result: dict[str, Any],
        readiness_result: dict[str, Any],
        mapping_result: dict[str, Any],
        validation_result: dict[str, Any],
        import_result: dict[str, Any],
    ) -> OracleReport:
        """Run all oracles and generate report.
        
        Args:
            discovery_result: Discovery output
            corpus_result: Corpus assignment output
            readiness_result: Readiness assessment output
            mapping_result: Mapping output
            validation_result: Validation output
            import_result: Import execution output
        
        Returns:
            Complete oracle report
        """
        stage_results = [
            self._validate_discovery(discovery_result),
            self._validate_corpus(corpus_result),
            self._validate_readiness(readiness_result),
            self._validate_mapping(mapping_result),
            self._validate_validation(validation_result),
            self._validate_import(import_result),
        ]

        all_passed = all(r.passed for r in stage_results)
        first_failure = next(
            (r.stage for r in stage_results if not r.passed), None
        )
        overall_score = sum(r.score for r in stage_results) / len(stage_results)

        return OracleReport(
            scenario_name=self.scenario.name,
            timestamp=datetime.utcnow(),
            stage_results=stage_results,
            all_passed=all_passed,
            first_failure_stage=first_failure,
            overall_score=overall_score,
        )

    def _validate_discovery(
        self, discovery_result: dict[str, Any]
    ) -> StageOracleResult:
        """Validate discovery MVP boundary.
        
        Args:
            discovery_result: Discovery output (ProjectTargetStructure data)
        
        Returns:
            Discovery oracle result
        """
        target_structure = discovery_result.get("target_structure_json", {})
        actual_seeds = set(target_structure.get("seed_doctypes", []))
        expected_seeds = set(self.scenario.expected_mvp.seed_doctypes)

        diffs = []

        # Check for missing seeds
        missing = expected_seeds - actual_seeds
        if missing:
            diffs.append(
                OracleDiff(
                    expected=list(expected_seeds),
                    actual=list(actual_seeds),
                    diff_type="missing",
                    details=f"Missing seed doctypes: {missing}",
                )
            )

        # Check for extra seeds (scope creep)
        extra = actual_seeds - expected_seeds
        if extra:
            diffs.append(
                OracleDiff(
                    expected=list(expected_seeds),
                    actual=list(actual_seeds),
                    diff_type="extra",
                    details=f"Unexpected seed doctypes: {extra}",
                )
            )

        passed = len(diffs) == 0
        score = 1.0 if passed else (1.0 - len(diffs) / max(len(expected_seeds), 1))
        message = "Discovery MVP matches expected" if passed else f"Discovery failed: {len(diffs)} issues"

        return StageOracleResult(
            stage=OracleStage.DISCOVERY,
            passed=passed,
            diffs=diffs,
            score=max(0.0, score),
            message=message,
        )

    def _validate_corpus(
        self, corpus_result: dict[str, Any]
    ) -> StageOracleResult:
        """Validate corpus file-doctype assignments.
        
        Args:
            corpus_result: Corpus assignment artifact
        
        Returns:
            Corpus oracle result
        """
        assignments = corpus_result.get("assignments", {})
        expected_map = {
            stub.filename: stub.expected_doctype
            for stub in self.scenario.corpus_files
        }

        diffs = []

        for filename, expected_doctype in expected_map.items():
            actual_doctype = assignments.get(filename)
            if actual_doctype != expected_doctype:
                diffs.append(
                    OracleDiff(
                        expected=expected_doctype,
                        actual=actual_doctype,
                        diff_type="mismatch",
                        details=f"File {filename}: expected {expected_doctype}, got {actual_doctype}",
                    )
                )

        passed = len(diffs) == 0
        score = 1.0 if passed else (1.0 - len(diffs) / max(len(expected_map), 1))
        message = "Corpus assignments match expected" if passed else f"Corpus failed: {len(diffs)} mismatches"

        return StageOracleResult(
            stage=OracleStage.CORPUS,
            passed=passed,
            diffs=diffs,
            score=max(0.0, score),
            message=message,
        )

    def _validate_readiness(
        self, readiness_result: dict[str, Any]
    ) -> StageOracleResult:
        """Validate readiness assessment gaps.
        
        Args:
            readiness_result: Readiness assessment data
        
        Returns:
            Readiness oracle result
        """
        # Placeholder: compare gaps_identified vs expected_gaps
        # For MVP, lenient validation (just check minimum_viable_import_possible)
        is_viable = readiness_result.get("minimum_viable_import_possible", False)
        expected_viable = len(self.scenario.expected_mvp.seed_doctypes) > 0

        diffs = []
        if is_viable != expected_viable:
            diffs.append(
                OracleDiff(
                    expected=expected_viable,
                    actual=is_viable,
                    diff_type="mismatch",
                    details=f"Import viability: expected {expected_viable}, got {is_viable}",
                )
            )

        passed = len(diffs) == 0
        score = 1.0 if passed else 0.5
        message = "Readiness assessment correct" if passed else "Readiness viability mismatch"

        return StageOracleResult(
            stage=OracleStage.READINESS,
            passed=passed,
            diffs=diffs,
            score=score,
            message=message,
        )

    def _validate_mapping(
        self, mapping_result: dict[str, Any]
    ) -> StageOracleResult:
        """Validate mapped CSV files.
        
        Args:
            mapping_result: Mapping output (file counts, mapped doctypes)
        
        Returns:
            Mapping oracle result
        """
        mapped_count = mapping_result.get("mapped_count", 0)
        expected_count = len(self.scenario.corpus_files)

        diffs = []
        if mapped_count != expected_count:
            diffs.append(
                OracleDiff(
                    expected=expected_count,
                    actual=mapped_count,
                    diff_type="mismatch",
                    details=f"Mapped file count: expected {expected_count}, got {mapped_count}",
                )
            )

        passed = len(diffs) == 0
        score = 1.0 if passed else (mapped_count / max(expected_count, 1))
        message = "Mapping complete" if passed else f"Mapping incomplete: {mapped_count}/{expected_count}"

        return StageOracleResult(
            stage=OracleStage.MAPPING,
            passed=passed,
            diffs=diffs,
            score=max(0.0, score),
            message=message,
        )

    def _validate_validation(
        self, validation_result: dict[str, Any]
    ) -> StageOracleResult:
        """Validate validation report.
        
        Args:
            validation_result: Validation output
        
        Returns:
            Validation oracle result
        """
        # Placeholder: check if expected_validation_issues match actual
        # For MVP, lenient (just check no_critical_errors)
        has_errors = validation_result.get("has_errors", False)
        expected_errors = len(self.scenario.expected_validation_issues) > 0

        diffs = []
        if has_errors != expected_errors:
            diffs.append(
                OracleDiff(
                    expected=expected_errors,
                    actual=has_errors,
                    diff_type="mismatch",
                    details=f"Validation errors: expected {expected_errors}, got {has_errors}",
                )
            )

        passed = len(diffs) == 0
        score = 1.0 if passed else 0.5
        message = "Validation correct" if passed else "Validation error mismatch"

        return StageOracleResult(
            stage=OracleStage.VALIDATION,
            passed=passed,
            diffs=diffs,
            score=score,
            message=message,
        )

    def _validate_import(
        self, import_result: dict[str, Any]
    ) -> StageOracleResult:
        """Validate import execution and ERPNext records.
        
        Args:
            import_result: Import output (record counts, errors)
        
        Returns:
            Import oracle result
        """
        actual_counts = import_result.get("record_counts", {})
        expected_counts = self.scenario.expected_record_counts

        diffs = []
        for doctype, expected_count in expected_counts.items():
            actual_count = actual_counts.get(doctype, 0)
            if actual_count != expected_count:
                diffs.append(
                    OracleDiff(
                        expected=expected_count,
                        actual=actual_count,
                        diff_type="mismatch",
                        details=f"{doctype}: expected {expected_count} records, got {actual_count}",
                    )
                )

        passed = len(diffs) == 0
        score = 1.0 if passed else (1.0 - len(diffs) / max(len(expected_counts), 1))
        message = "Import records match expected" if passed else f"Import failed: {len(diffs)} count mismatches"

        return StageOracleResult(
            stage=OracleStage.IMPORT,
            passed=passed,
            diffs=diffs,
            score=max(0.0, score),
            message=message,
        )
