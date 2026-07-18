"""
Step 2 corpus harness — offline golden gate + optional live LLM (Phase 3).

  python -m containers.implementation.corpus.test.harness_corpus --fixture green_surface
  python -m containers.implementation.corpus.test.harness_corpus --manifest path/to/manifest.json
  python -m containers.implementation.corpus.test.harness_corpus --fixture green_surface --live-llm
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from containers.implementation.corpus.checkers import evaluate_step2_gate

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _load_fixture(name: str) -> Dict[str, Any]:
    path = FIXTURES_DIR / f"{name}_manifest.json"
    if not path.exists():
        raise SystemExit(f"Unknown fixture: {name} (expected {path})")
    return json.loads(path.read_text(encoding="utf-8"))


def _run_offline_gate(manifest: Dict[str, Any], *, label: str) -> int:
    golden = manifest.pop("_golden", None) or {}
    result = evaluate_step2_gate(
        manifest,
        file_doctype_expectations=golden.get("file_doctype_expectations"),
        file_exclusion_expectations=golden.get("file_exclusion_expectations"),
    )

    _print_header(f"Step 2 gate — {label}")
    print(f"  status:           {result.status}")
    print(f"  passed:           {result.passed}")
    print(f"  manifest_ok:      {result.manifest_ok}")
    print(f"  understanding_ok: {result.understanding_ok}")

    if result.issues:
        print()
        print("  Issues:")
        for issue in result.issues:
            print(f"    [{issue.severity}] {issue.code}: {issue.message}")

    return 0 if result.passed else 1


async def _run_live_enrich(
    manifest: Dict[str, Any],
    *,
    discovery_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from containers.implementation.corpus.enrich_understanding import (
        _build_files_block,
        _extract_discovery_context,
    )
    from containers.implementation.corpus.prompts import CORPUS_UNDERSTANDING_PROMPT
    from containers.implementation.corpus.schemas import CorpusUnderstanding
    from containers.implementation.corpus.validation import (
        merge_missing_file_entries,
        validate_corpus_understanding,
    )
    from containers.implementation.corpus.manifest import extract_files_from_manifest
    from shared.llm_schema_utils import repair_pydantic_dict
    from shared.structured_llm import generate_typed

    files = extract_files_from_manifest(manifest)
    expected = list(files.keys())
    discovery_context = _extract_discovery_context(None, discovery_metadata)
    prompt = CORPUS_UNDERSTANDING_PROMPT.format(
        discovery_context=discovery_context,
        user_import_note="(harness)",
        files_block=_build_files_block(manifest),
    )
    llm_result = await generate_typed(
        prompt=prompt,
        schema=CorpusUnderstanding,
        temperature=0.1,
        max_output_tokens=4000,
    )
    understanding = CorpusUnderstanding.model_validate(
        repair_pydantic_dict(llm_result, CorpusUnderstanding)
    )
    understanding = merge_missing_file_entries(understanding, expected)
    status, warnings = validate_corpus_understanding(understanding, expected)
    manifest["corpus_understanding"] = understanding.model_dump()
    manifest["corpus_understanding"]["_validation"] = {"status": status, "warnings": warnings}
    return manifest


async def _async_main(args: argparse.Namespace) -> int:
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        label = Path(args.manifest).name
    elif args.fixture:
        manifest = _load_fixture(args.fixture)
        label = args.fixture
    else:
        raise SystemExit("Provide --fixture or --manifest")

    if args.live_llm:
        _print_header(f"Live LLM enrich — {label}")
        manifest = await _run_live_enrich(manifest)
        if args.fixture:
            manifest["_golden"] = _load_fixture(args.fixture).get("_golden")

    return _run_offline_gate(manifest, label=label)


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 2 corpus harness")
    parser.add_argument("--fixture", help="Fixture name (e.g. green_surface)")
    parser.add_argument("--manifest", help="Path to manifest JSON")
    parser.add_argument("--live-llm", action="store_true", help="Run live LLM enrich (Phase 3)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_async_main(args)))


if __name__ == "__main__":
    main()
