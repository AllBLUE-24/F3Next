#!/usr/bin/env python3
"""
v1.0.0 foundation regression — run all automated gates before rc tag.

Usage:
  python scripts/verify_foundation.py
  python scripts/verify_foundation.py --skip-frontend
  python scripts/verify_foundation.py --skip-smoke-llm
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], *, cwd: Path | None = None, label: str = "") -> int:
    print(f"\n{'=' * 60}\n{label or ' '.join(cmd)}\n{'=' * 60}")
    executable = cmd[0]
    if executable == "npm" and sys.platform == "win32":
        cmd = ["npm.cmd", *cmd[1:]]
    result = subprocess.run(cmd, cwd=cwd or ROOT, shell=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="v1.0.0 foundation verification")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-smoke-llm", action="store_true")
    parser.add_argument("--skip-sync-kb", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []

    steps: list[tuple[str, list[str], Path | None]] = [
        (
            "Foundation unit tests (shared + OS + IS)",
            [
                sys.executable,
                "-m",
                "pytest",
                "shared/tests",
                "containers/os/tests",
                "containers/implementation/tests",
                "-q",
            ],
            ROOT,
        ),
    ]

    if not args.skip_sync_kb:
        steps.append(
            (
                "KB autofill sync check",
                [sys.executable, "scripts/sync_autofill_from_kb.py", "--check"],
                ROOT,
            )
        )

    if not args.skip_smoke_llm:
        steps.append(
            ("L0 LLM smoke", [sys.executable, "-m", "shared.smoke_llm"], ROOT),
        )

    if not args.skip_frontend:
        steps.extend([
            (
                "Frontend unit tests",
                ["npm", "run", "test"],
                ROOT / "frontend",
            ),
        ])

    for label, cmd, cwd in steps:
        code = run(cmd, cwd=cwd, label=label)
        if code != 0:
            failures.append(label)

    print("\n" + "=" * 60)
    if failures:
        print("FOUNDATION VERIFY: FAILED")
        for f in failures:
            print(f"  - {f}")
        print("\nManual golden matrix still required — see docs/v1.0.0/FOUNDATION_VERIFICATION.md")
        return 1

    print("FOUNDATION VERIFY: ALL AUTOMATED CHECKS PASSED")
    print("Next: rebuild workers + run manual golden rows (FOUNDATION_VERIFICATION.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
