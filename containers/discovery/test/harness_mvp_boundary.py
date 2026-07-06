"""
MVP boundary harness — runs the same path as discovery finalize (minus DB).

Provide only what a user would say. LLM extract + recommend run by default, then
niche resolution and build_discovery_target.

  python -m containers.discovery.test.harness_mvp_boundary
  python -m containers.discovery.test.harness_mvp_boundary --transcript-file story.txt
  python -m containers.discovery.test.harness_mvp_boundary --transcript-file story.txt --report
  python -m containers.discovery.test.harness_mvp_boundary --transcript-file story.txt --report --expect-archetype factory_wip_bridge
  python -m containers.discovery.test.harness_mvp_boundary --messages-file chat.json
  python -m containers.discovery.test.harness_mvp_boundary --matrix --report

Requires LLM credentials (same as discovery). Use --no-llm only for offline scoping
debug (skips extract/recommend; not a full pipeline test).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from containers.discovery.prompts import OPENING_MESSAGE
from containers.discovery.utils import normalize_messages, transcript_text


def _print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _read_interactive_story() -> str:
    print("Paste what the user said in discovery (finish with a blank line):")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        raise SystemExit("No user text provided.")
    return text


def _messages_from_user_text(user_text: str) -> list[dict]:
    return [
        {"role": "assistant", "content": OPENING_MESSAGE},
        {"role": "user", "content": user_text.strip()},
    ]


def _load_messages(args: argparse.Namespace) -> list[dict]:
    if args.messages_file:
        raw = json.loads(Path(args.messages_file).read_text(encoding="utf-8"))
        messages = normalize_messages(raw)
        if not any(m.get("role") == "user" for m in messages):
            raise SystemExit("--messages-file must include at least one user message.")
        return messages

    user_text = args.transcript
    if args.transcript_file:
        user_text = Path(args.transcript_file).read_text(encoding="utf-8").strip()
    if not user_text:
        user_text = _read_interactive_story()
    return _messages_from_user_text(user_text)


async def _run_with_llm(messages: list[dict], *, enhance_target: bool, use_llm_niche: bool | None) -> dict[str, Any]:
    from containers.discovery.chat_service import complete_discovery
    from containers.discovery.target.build_target import build_discovery_target

    chat_transcript = transcript_text(messages)

    discovery = await complete_discovery(messages, use_llm_niche=use_llm_niche)
    metadata = discovery["discovery_metadata"]
    coverage = discovery["coverage"]

    broad_f3iche = metadata.get("f3iche", discovery.get("broad_f3iche", "trading"))
    industry = metadata.get("industry", "")
    mvp_focus = metadata.get("mvp_focus") or {}
    niche_id = metadata.get("f3iche_niche") or discovery.get("f3iche_niche")
    niche_source = metadata.get("niche_resolution_source") or discovery.get("niche_resolution_source")

    target = await build_discovery_target(
        f3iche=niche_id,
        mvp_focus=mvp_focus,
        coverage=coverage,
        chat_transcript=chat_transcript,
        discovery_chat=messages,
        enhance_with_llm=enhance_target,
        niche_resolution_source=niche_source,
    )

    return {
        "pipeline": "llm",
        "messages": messages,
        "chat_transcript": chat_transcript,
        "coverage": coverage,
        "recommendation": discovery["recommendation"],
        "discovery_metadata": metadata,
        "niche_id": niche_id,
        "niche_resolution_source": niche_source,
        "broad_f3iche": broad_f3iche,
        "industry": industry,
        "mvp_focus": mvp_focus,
        "target": target,
        "mvp_boundary": target.get("mvp_boundary", {}),
        "scoping": target.get("scoping", {}),
    }


def _run_without_llm(messages: list[dict], *, f3iche_override: str | None) -> dict[str, Any]:
    from containers.discovery.niche_resolver import resolve_discovery_f3iche_niche
    from containers.discovery.mvp_scoping import scope_mvp_seeds
    from containers.discovery.niche_resolver import f3iche_template_path
    from containers.discovery.target.f3iche_seeds import load_f3iche_template_seeds

    chat_transcript = transcript_text(messages)
    niche_id = f3iche_override or resolve_discovery_f3iche_niche(
        discovery_f3iche="manufacturing",
        industry="",
        chat_transcript=chat_transcript,
    )
    seeds, f3iche_data = load_f3iche_template_seeds(str(f3iche_template_path(niche_id)))
    scoping = scope_mvp_seeds(
        template_seeds=seeds,
        f3iche_id=niche_id,
        f3iche_data=f3iche_data,
        mvp_focus=None,
        coverage=None,
        chat_transcript=chat_transcript,
    )
    mvp_boundary = {
        "mode": scoping["scoping_mode"],
        "f3iche": niche_id,
        "seed_doctypes": scoping["mvp_seeds"],
        "deferred_doctypes": scoping["deferred_seeds"],
        "template_seeds": seeds,
        "mvp_focus": {},
        "scoping_reasoning": scoping["scoping_reasoning"],
        "dual_system_note": scoping.get("dual_system_note", ""),
        "archetype_id": scoping.get("archetype_id"),
        "archetype_source": scoping.get("archetype_source"),
        "signal_match_score": scoping.get("signal_match_score"),
        "signal_match_candidates": scoping.get("signal_match_candidates") or [],
        "llm_archetype_id": scoping.get("llm_archetype_id"),
        "llm_archetype_signal_score": scoping.get("llm_archetype_signal_score"),
        "chosen_archetype_signal_score": scoping.get("chosen_archetype_signal_score"),
        "archetype_routing_mismatch": scoping.get("archetype_routing_mismatch", False),
        "archetype_routing_note": scoping.get("archetype_routing_note"),
    }
    return {
        "pipeline": "no_llm_scoping_only",
        "messages": messages,
        "chat_transcript": chat_transcript,
        "niche_id": niche_id,
        "mvp_boundary": mvp_boundary,
        "scoping": scoping,
    }


def _print_signal_routing_report(result: dict[str, Any]) -> None:
    mvp = result.get("mvp_boundary") or {}
    scoping = result.get("scoping") or {}
    focus = result.get("mvp_focus") or mvp.get("mvp_focus") or {}

    candidates = mvp.get("signal_match_candidates") or scoping.get("signal_match_candidates") or []
    llm_id = focus.get("archetype_id") or mvp.get("llm_archetype_id")
    scoped_id = mvp.get("archetype_id") or scoping.get("archetype_id")
    source = mvp.get("archetype_source") or scoping.get("archetype_source")

    _print_header("SIGNAL ROUTING DIAGNOSTICS")
    print(f"  LLM archetype_id:              {llm_id}")
    print(f"  Scoped archetype_id:           {scoped_id}")
    print(f"  archetype_source:              {source}")
    print(f"  signal_match_score (fallback): {mvp.get('signal_match_score') or scoping.get('signal_match_score')}")
    print(f"  llm_archetype_signal_score:    {mvp.get('llm_archetype_signal_score') or scoping.get('llm_archetype_signal_score')}")
    print(f"  chosen_archetype_signal_score: {mvp.get('chosen_archetype_signal_score') or scoping.get('chosen_archetype_signal_score')}")

    mismatch = mvp.get("archetype_routing_mismatch") or scoping.get("archetype_routing_mismatch")
    note = mvp.get("archetype_routing_note") or scoping.get("archetype_routing_note")
    if mismatch:
        print(f"  ⚠ routing_mismatch:            YES — {note}")
    else:
        print("  routing_mismatch:              no")

    print()
    print("  Top signal_match_candidates:")
    if not candidates:
        print("    (none — no signal hits at min score 1)")
    for row in candidates:
        marker = " ← top" if row == candidates[0] else ""
        print(f"    - {row.get('archetype_id')}: score {row.get('score')}{marker}")


_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_LIVE_MATRIX_PATH = _FIXTURES_DIR / "live_routing_matrix.json"


def _load_live_matrix() -> dict[str, Any]:
    return json.loads(_LIVE_MATRIX_PATH.read_text(encoding="utf-8"))


def _live_matrix_cases() -> list[dict[str, Any]]:
    return list(_load_live_matrix().get("cases") or [])


def _accepted_archetypes_for_case(case: dict[str, Any]) -> set[str]:
    ids = {str(case["expect_archetype"]).strip()}
    for alt in case.get("accept_alternate_archetypes") or []:
        ids.add(str(alt).strip())
    return ids


def _case_archetype_pass(case: dict[str, Any], result: dict[str, Any]) -> tuple[bool, str]:
    mvp = result.get("mvp_boundary") or {}
    scoping = result.get("scoping") or {}
    focus = result.get("mvp_focus") or mvp.get("mvp_focus") or {}
    llm_id = str(focus.get("archetype_id") or "").strip()
    scoped_id = str(mvp.get("archetype_id") or scoping.get("archetype_id") or "").strip()
    if llm_id.lower() in ("null", "none"):
        llm_id = ""
    accepted = _accepted_archetypes_for_case(case)
    if scoped_id in accepted:
        return True, f"scoped {scoped_id!r}"
    if llm_id in accepted:
        return True, f"LLM {llm_id!r} (scoped {scoped_id!r})"
    top = (mvp.get("signal_match_candidates") or scoping.get("signal_match_candidates") or [])
    top_id = top[0]["archetype_id"] if top else None
    return False, f"expected {sorted(accepted)!r}; LLM={llm_id!r}, scoped={scoped_id!r}, top_signal={top_id!r}"


async def _run_live_matrix(
    *,
    enhance_target: bool,
    use_llm_niche: bool | None,
    report: bool,
    quiet: bool,
) -> tuple[list[dict[str, Any]], float, int]:
    matrix = _load_live_matrix()
    gate = float((matrix.get("_meta") or {}).get("gate_min_accuracy") or 0.8)
    cases = [c for c in _live_matrix_cases() if not c.get("deterministic_only")]

    rows: list[dict[str, Any]] = []
    passed = 0
    for case in cases:
        fixture = _FIXTURES_DIR / case["fixture"]
        user_text = fixture.read_text(encoding="utf-8").strip()
        messages = _messages_from_user_text(user_text)
        result = await _run_with_llm(messages, enhance_target=enhance_target, use_llm_niche=use_llm_niche)
        ok, msg = _case_archetype_pass(case, result)
        if ok:
            passed += 1
        row = {
            "id": case.get("id"),
            "name": case.get("name"),
            "fixture": case.get("fixture"),
            "pass": ok,
            "detail": msg,
            "niche_id": result.get("niche_id"),
            "result": result,
        }
        rows.append(row)

        if not quiet:
            status = "PASS" if ok else "FAIL"
            print(f"\n[{status}] {case.get('id')} — {case.get('name')}")
            print(f"  {msg}")
            if report:
                _print_signal_routing_report(result)

    accuracy = passed / len(cases) if cases else 0.0
    if not quiet:
        _print_header("LIVE ROUTING MATRIX SUMMARY")
        print(f"  Passed:   {passed}/{len(cases)} ({accuracy:.0%})")
        print(f"  Gate:     {gate:.0%} minimum")
        print(f"  Status:   {'GREEN' if accuracy >= gate else 'RED'}")
    return rows, accuracy, 0 if accuracy >= gate else 1


def _check_expect_archetype(result: dict[str, Any], expected: str) -> tuple[bool, str]:
    mvp = result.get("mvp_boundary") or {}
    scoping = result.get("scoping") or {}
    focus = result.get("mvp_focus") or mvp.get("mvp_focus") or {}
    llm_id = str(focus.get("archetype_id") or "").strip()
    scoped_id = str(mvp.get("archetype_id") or scoping.get("archetype_id") or "").strip()
    expected = expected.strip()

    if llm_id.lower() in ("null", "none"):
        llm_id = ""

    if scoped_id == expected:
        return True, f"scoped archetype {scoped_id!r} matches expected"
    if llm_id == expected:
        return True, f"LLM archetype {llm_id!r} matches expected (scoped: {scoped_id!r})"
    top = (mvp.get("signal_match_candidates") or scoping.get("signal_match_candidates") or [])
    top_id = top[0]["archetype_id"] if top else None
    return False, (
        f"expected {expected!r}; LLM={llm_id!r}, scoped={scoped_id!r}, top_signal={top_id!r}"
    )


def _print_coverage(coverage: dict[str, Any]) -> None:
    _print_header("COVERAGE (LLM extract)")
    for dim, entry in (coverage or {}).items():
        val = (entry or {}).get("value")
        if val:
            print(f"  {dim}: {val}")


def _print_mvp_focus(mvp_focus: dict[str, Any]) -> None:
    _print_header("MVP FOCUS (LLM recommend)")
    print(f"  primary_bottleneck: {mvp_focus.get('primary_bottleneck', '')}")
    print(f"  archetype_id:       {mvp_focus.get('archetype_id', '')}")
    reqs = mvp_focus.get("functional_requirements") or []
    if reqs:
        print("  functional_requirements:")
        for req in reqs:
            print(f"    - {req}")


def _print_result(result: dict[str, Any]) -> None:
    if result.get("pipeline") == "llm":
        _print_header("RESOLVED")
        print(f"  broad_f3iche: {result.get('broad_f3iche')}")
        print(f"  industry:     {result.get('industry')}")
        print(f"  niche_id:     {result.get('niche_id')}")
        print(f"  niche_source: {result.get('niche_resolution_source', '')}")
        _print_coverage(result.get("coverage") or {})
        _print_mvp_focus(result.get("mvp_focus") or {})

    mvp = result.get("mvp_boundary") or {}
    scoping = result.get("scoping") or {}

    _print_header("MVP BOUNDARY")
    print(f"  f3iche:              {mvp.get('f3iche') or result.get('niche_id', '')}")
    print(f"  mode:                {mvp.get('mode') or scoping.get('scoping_mode', '')}")
    focus = mvp.get("mvp_focus") or result.get("mvp_focus") or {}
    print(f"  primary_bottleneck:  {focus.get('primary_bottleneck', '')}")
    print(f"  archetype_id:        {focus.get('archetype_id', '')}")
    print(f"  scoping_reasoning:   {mvp.get('scoping_reasoning') or scoping.get('scoping_reasoning', '')}")
    dual = mvp.get("dual_system_note") or scoping.get("dual_system_note", "")
    if dual:
        print(f"  dual_system_note:    {dual}")

    seeds = mvp.get("seed_doctypes") or scoping.get("mvp_seeds") or []
    deferred = mvp.get("deferred_doctypes") or scoping.get("deferred_seeds") or []
    print()
    print(f"  Day-1 seed_doctypes ({len(seeds)}):")
    for dt in seeds:
        print(f"    - {dt}")
    print()
    print(f"  deferred_doctypes ({len(deferred)}):")
    for dt in deferred:
        print(f"    - {dt}")

    target = result.get("target") or {}
    required = target.get("required_doctypes") or []
    if required:
        print()
        print(f"  graph-expanded required_doctypes ({len(required)}):")
        for dt in required[:20]:
            print(f"    - {dt}")
        if len(required) > 20:
            print(f"    ... +{len(required) - 20} more")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run discovery finalize pipeline on user text and print MVP boundary.",
    )
    p.add_argument(
        "--transcript",
        help="Single user message (what they said in discovery)",
    )
    p.add_argument(
        "--transcript-file",
        help="File containing the user's discovery story (plain text)",
    )
    p.add_argument(
        "--messages-file",
        help="Full chat history JSON [{role, content}, ...] including user turns",
    )
    p.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM extract/recommend; regex scoping on transcript only (debug)",
    )
    p.add_argument(
        "--no-target-llm",
        action="store_true",
        help="Keep extract/recommend LLM; skip build_target enhance_with_llm (currently no-op)",
    )
    p.add_argument(
        "--f3iche",
        help="Force niche template id (offline --no-llm only)",
    )
    p.add_argument(
        "--llm-niche",
        action="store_true",
        help="Enable DISCOVERY_LLM_NICHE_RESOLVE for this run (LLM picks F3iche niche)",
    )
    p.add_argument("--json-out", help="Write full pipeline result JSON to this path")
    p.add_argument("--quiet", action="store_true", help="Print MVP boundary JSON only")
    p.add_argument(
        "--report",
        action="store_true",
        help="Print signal routing diagnostics (shadow signal rankings vs LLM pick)",
    )
    p.add_argument(
        "--expect-archetype",
        help="With --report: exit 1 unless scoped or LLM archetype_id matches this id",
    )
    p.add_argument(
        "--matrix",
        action="store_true",
        help="Run live_routing_matrix.json cases (requires LLM; skips deterministic_only rows)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.matrix:
        if args.no_llm:
            raise SystemExit("--matrix requires live LLM (do not pass --no-llm)")
        use_llm_niche = True if args.llm_niche else None
        _, _, exit_code = asyncio.run(
            _run_live_matrix(
                enhance_target=not args.no_target_llm,
                use_llm_niche=use_llm_niche,
                report=args.report,
                quiet=args.quiet,
            )
        )
        return exit_code

    messages = _load_messages(args)

    if args.no_llm:
        result = _run_without_llm(messages, f3iche_override=args.f3iche)
    else:
        use_llm_niche = True if args.llm_niche else None
        result = asyncio.run(
            _run_with_llm(messages, enhance_target=not args.no_target_llm, use_llm_niche=use_llm_niche)
        )

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(result, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"Wrote {args.json_out}")

    if args.quiet:
        print(json.dumps(result.get("mvp_boundary") or {}, indent=2, default=str))
    else:
        _print_header("INPUT")
        print(result.get("chat_transcript") or transcript_text(messages))
        _print_result(result)
        if args.report:
            _print_signal_routing_report(result)
        _print_header("MVP BOUNDARY JSON")
        print(json.dumps(result.get("mvp_boundary") or {}, indent=2, default=str))

    if args.expect_archetype:
        ok, msg = _check_expect_archetype(result, args.expect_archetype)
        if args.report or args.quiet:
            print(f"\nexpect-archetype: {'PASS' if ok else 'FAIL'} — {msg}")
        if not ok:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
