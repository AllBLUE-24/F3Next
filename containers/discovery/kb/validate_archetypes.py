"""CLI: validate Discovery archetype catalog + F3iche bottlenecks before Research merge."""

from __future__ import annotations

import argparse
import sys

from containers.discovery.archetype_registry import validate_archetype_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate archetype_catalog.json and optional F3iche bottlenecks[]"
    )
    parser.add_argument(
        "--f3iche-id",
        default="manufacturing_project_chemical",
        help="F3iche id to merge-check (default: manufacturing_project_chemical)",
    )
    parser.add_argument(
        "--all-f3iches",
        action="store_true",
        help="Validate bottlenecks[] on every f3iches/*.json file",
    )
    parser.add_argument(
        "--warn-as-error",
        action="store_true",
        help="Exit non-zero on warnings too",
    )
    args = parser.parse_args(argv)

    result = validate_archetype_registry(
        args.f3iche_id if not args.all_f3iches else args.f3iche_id,
        check_all_f3iches=args.all_f3iches,
    )
    errors = result["errors"]
    warnings = result["warnings"]
    count = result["archetype_count"]

    print(f"Archetypes (merged with f3iche={args.f3iche_id!r}): {count}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1

    if args.warn_as_error and warnings:
        return 1

    print("\nOK — no validation errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
