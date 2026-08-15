"""Simulated user for responding to system prompts during tests."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from .schemas import CorpusFileStub, GapResponseTemplate, TestScenario


class SimulatedUser:
    """Simulates realistic user interactions for test scenarios."""

    def __init__(self, scenario: TestScenario):
        """Initialize simulated user with scenario context.
        
        Args:
            scenario: Test scenario defining expected behavior
        """
        self.scenario = scenario
        self._gap_response_map = {
            (r.doctype, r.gap_field): r for r in scenario.gap_responses
        }

    def respond_to_discovery_chat(self, question: str) -> str:
        """Respond to discovery chat clarification question.
        
        Args:
            question: Question from discovery chat
        
        Returns:
            Answer based on scenario context
        
        Note:
            For MVP, we just return the pain point verbatim.
            Advanced: use LLM with scenario context to answer follow-ups.
        """
        # For simplicity, always reiterate pain point
        return self.scenario.pain_point

    def generate_corpus_files(self, output_dir: Path) -> list[Path]:
        """Generate corpus files matching scenario stubs.
        
        Args:
            output_dir: Directory to save generated files
        
        Returns:
            Paths to generated files
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_paths = []

        for stub in self.scenario.corpus_files:
            file_path = output_dir / stub.filename
            
            if stub.filename.endswith(".csv"):
                self._generate_csv(stub, file_path)
            elif stub.filename.endswith((".xlsx", ".xls")):
                self._generate_excel(stub, file_path)
            else:
                raise ValueError(f"Unsupported file format: {stub.filename}")
            
            generated_paths.append(file_path)

        return generated_paths

    def _generate_csv(self, stub: CorpusFileStub, output_path: Path) -> None:
        """Generate CSV file from stub.
        
        Args:
            stub: Corpus file stub definition
            output_path: Where to save CSV
        """
        # Create header
        columns = stub.required_columns.copy()
        
        # Add some extra columns for realism
        if stub.expected_doctype == "Item":
            columns.extend(["description", "standard_rate"])
        elif stub.expected_doctype == "Work Order":
            columns.extend(["status", "company"])
        
        # Generate rows
        rows = []
        for i in range(1, stub.sample_row_count + 1):
            row = {}
            for col in columns:
                # Generate dummy values
                if col in stub.required_columns:
                    row[col] = f"{col}_{i}"
                else:
                    # Some fields left blank to simulate field_coverage_percent
                    if i % 5 == 0:  # 20% missing (80% coverage)
                        row[col] = ""
                    else:
                        row[col] = f"{col}_{i}"
            rows.append(row)
        
        # Write CSV
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def _generate_excel(self, stub: CorpusFileStub, output_path: Path) -> None:
        """Generate Excel file from stub.
        
        Args:
            stub: Corpus file stub definition
            output_path: Where to save Excel
        
        Note:
            Placeholder - requires openpyxl/xlsxwriter.
            For MVP, convert to CSV or use pandas.
        """
        # TODO: Implement Excel generation
        # For now, generate CSV with .xlsx extension (will fail in real usage)
        csv_path = output_path.with_suffix(".csv")
        self._generate_csv(stub, csv_path)
        # Optionally: convert CSV to Excel using pandas
        # import pandas as pd
        # df = pd.read_csv(csv_path)
        # df.to_excel(output_path, index=False)

    def respond_to_gap_question(
        self, doctype: str, field: str, gap_details: dict[str, Any]
    ) -> str:
        """Respond to data gap question.
        
        Args:
            doctype: Doctype with gap
            field: Field name with gap
            gap_details: Additional gap context from readiness
        
        Returns:
            Response value or directive
        """
        # Lookup response template
        key = (doctype, field)
        template = self._gap_response_map.get(key)

        if template is None:
            # Default: provide generic value
            return f"Default {field}"

        if template.response_type == "provide_value":
            return template.value or f"Default {field}"
        elif template.response_type == "defer":
            return "DEFER_TO_POST_MVP"
        elif template.response_type == "skip":
            return "SKIP_FIELD"
        else:
            return f"Default {field}"

    def respond_to_upload_prompt(
        self, upload_schema: dict[str, Any], output_dir: Path
    ) -> list[Path]:
        """Respond to upload prompt by generating required files.
        
        Args:
            upload_schema: Schema from build_upload_schema_preview
            output_dir: Directory to save files
        
        Returns:
            Paths to uploaded files
        """
        # For test scenarios, ignore upload_schema and just generate from stubs
        # (upload_schema should match scenario expectations anyway)
        return self.generate_corpus_files(output_dir)
