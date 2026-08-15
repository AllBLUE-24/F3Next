"""Main orchestrator for test harness execution loop."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .diagnostician import Diagnostician
from .oracle import Oracle
from .schemas import TestResult, TestScenario, TestStatus
from .simulated_user import SimulatedUser


class TestRunner:
    """Orchestrates end-to-end test execution."""

    def __init__(self, config_path: Path | None = None):
        """Initialize test runner with configuration.
        
        Args:
            config_path: Path to config.json (defaults to .skills/test-harness/config.json)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "config.json"

        with open(config_path) as f:
            self.config = json.load(f)

    def run_scenario(
        self,
        scenario: TestScenario,
        implement_fixes: bool = False,
        max_iterations: int = 3,
    ) -> TestResult:
        """Run a single test scenario.
        
        Args:
            scenario: Test scenario to execute
            implement_fixes: Whether to auto-implement fixes on failure
            max_iterations: Max fix-retry iterations
        
        Returns:
            Test result
        """
        start_time = time.time()
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            print(f"\n=== Running scenario: {scenario.name} (iteration {iteration}) ===\n")

            try:
                # 1. Initialize simulated user
                user = SimulatedUser(scenario)

                # 2. Execute pipeline (placeholder - integrate with real workflow)
                pipeline_results = self._execute_pipeline(scenario, user)

                # 3. Run oracles
                oracle = Oracle(scenario)
                oracle_report = oracle.validate_all(**pipeline_results)

                # 4. Check if passed
                if oracle_report.all_passed:
                    duration = time.time() - start_time
                    return TestResult(
                        scenario_name=scenario.name,
                        status=TestStatus.PASSED,
                        timestamp=datetime.utcnow(),
                        duration_seconds=duration,
                        oracle_report=oracle_report,
                        fixed_by_iteration=iteration if iteration > 1 else None,
                    )

                # 5. Diagnose failure
                diagnostician = Diagnostician()
                diagnostic_report = diagnostician.diagnose(oracle_report, scenario)

                print(f"\n=== Diagnostician Report ===")
                print(f"Failed Stage: {diagnostic_report.failed_stage}")
                print(f"Layer: {diagnostic_report.layer}")
                print(f"Fix Type: {diagnostic_report.fix_type}")
                print(f"Root Cause: {diagnostic_report.root_cause}")
                print(f"Confidence: {diagnostic_report.confidence}")
                print(f"\nProposed Changes:")
                for change in diagnostic_report.proposed_changes:
                    print(f"  - {change.file_path}: {change.description}")

                # 6. Human gate + implementation
                if implement_fixes:
                    approved = self._ask_user_approval(diagnostic_report)
                    if approved:
                        self._apply_fixes(diagnostic_report)
                        print("\n=== Fixes applied. Re-running scenario... ===\n")
                        continue  # Retry
                    else:
                        print("\n=== Fix rejected by user. Stopping. ===\n")
                        duration = time.time() - start_time
                        return TestResult(
                            scenario_name=scenario.name,
                            status=TestStatus.FAILED,
                            timestamp=datetime.utcnow(),
                            duration_seconds=duration,
                            oracle_report=oracle_report,
                            diagnostic_report=diagnostic_report,
                        )
                else:
                    # No auto-fix, return failure
                    duration = time.time() - start_time
                    return TestResult(
                        scenario_name=scenario.name,
                        status=TestStatus.FAILED,
                        timestamp=datetime.utcnow(),
                        duration_seconds=duration,
                        oracle_report=oracle_report,
                        diagnostic_report=diagnostic_report,
                    )

            except Exception as e:
                duration = time.time() - start_time
                return TestResult(
                    scenario_name=scenario.name,
                    status=TestStatus.ERROR,
                    timestamp=datetime.utcnow(),
                    duration_seconds=duration,
                    error_message=str(e),
                )

        # Max iterations reached without pass
        duration = time.time() - start_time
        return TestResult(
            scenario_name=scenario.name,
            status=TestStatus.FAILED,
            timestamp=datetime.utcnow(),
            duration_seconds=duration,
            error_message=f"Max iterations ({max_iterations}) reached without resolution",
        )

    def _execute_pipeline(
        self, scenario: TestScenario, user: SimulatedUser
    ) -> dict[str, Any]:
        """Execute F3Next implementation pipeline.
        
        Args:
            scenario: Test scenario
            user: Simulated user for interactions
        
        Returns:
            Pipeline results for each stage
        
        Note:
            Placeholder - integrate with real Temporal workflow or step harnesses.
        """
        # TODO: Integrate with real pipeline execution
        # For MVP, return mock results
        return {
            "discovery_result": {
                "target_structure_json": {
                    "seed_doctypes": scenario.expected_mvp.seed_doctypes,
                }
            },
            "corpus_result": {
                "assignments": {
                    stub.filename: stub.expected_doctype
                    for stub in scenario.corpus_files
                }
            },
            "readiness_result": {
                "minimum_viable_import_possible": True,
            },
            "mapping_result": {
                "mapped_count": len(scenario.corpus_files),
            },
            "validation_result": {
                "has_errors": len(scenario.expected_validation_issues) > 0,
            },
            "import_result": {
                "record_counts": scenario.expected_record_counts,
            },
        }

    def _ask_user_approval(self, diagnostic_report: Any) -> bool:
        """Ask user to approve proposed fixes.
        
        Args:
            diagnostic_report: Diagnostician report
        
        Returns:
            True if approved, False otherwise
        """
        # Placeholder - integrate with Cursor AskQuestion or CLI input
        print("\n=== Awaiting user approval for fixes ===")
        response = input("Approve fixes? (y/n): ").strip().lower()
        return response == "y"

    def _apply_fixes(self, diagnostic_report: Any) -> None:
        """Apply proposed fixes.
        
        Args:
            diagnostic_report: Diagnostician report
        """
        # Placeholder - integrate with code editing tools
        print("\n=== Applying fixes ===")
        for change in diagnostic_report.proposed_changes:
            print(f"  - Applying: {change.file_path} ({change.change_type})")
            # TODO: Use StrReplace, Write, etc. to apply changes
        print("=== Fixes applied ===")


# Import here to avoid circular dependency
from datetime import datetime
