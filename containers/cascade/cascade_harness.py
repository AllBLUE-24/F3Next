"""
Cascade harness — preview rule matching and messages without Temporal.

Usage:
    python -m containers.cascade.cascade_harness --doctype "Sales Order" --event on_submit --payload '{"name":"SO-001","customer":"Acme","grand_total":120000}'
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv

load_dotenv(_root / ".env")


def _install_fake_activity_context() -> None:
    try:
        import temporalio.activity as _ta

        class _FakeActivity:
            @staticmethod
            def heartbeat(*args, **kwargs):
                pass

        if not getattr(_ta, "_f3next_harness_patched", False):
            _ta.logger = __import__("logging").getLogger("cascade_harness")
            _ta.heartbeat = _FakeActivity.heartbeat
            _ta._f3next_harness_patched = True
    except ImportError:
        pass


async def preview(doctype: str, trigger_event: str, payload: dict) -> None:
    _install_fake_activity_context()

    from containers.cascade.rule_resolver.activities import resolve_cascade_rules
    from containers.cascade.translator.activities import translate_event_to_messages

    rules = await resolve_cascade_rules({
        "doctype": doctype,
        "trigger_event": trigger_event,
        "event_payload": payload,
    })
    translated = await translate_event_to_messages({
        "matched_rules": rules.get("matched_rules") or [],
        "template_context": rules.get("template_context") or {},
        "risk_tier": rules.get("risk_tier"),
    })

    print("\n=== Cascade preview ===")
    print(f"Doctype:       {doctype}")
    print(f"Trigger event: {trigger_event}")
    print(f"Risk tier:     {rules.get('risk_tier')}")
    print(f"Matched rules: {len(rules.get('matched_rules') or [])}")
    print()

    for msg in translated.get("messages") or []:
        print(f"[{msg.get('department')}] {msg.get('title')}")
        print(f"  {msg.get('body')}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview cascade rule matching")
    parser.add_argument("--doctype", required=True)
    parser.add_argument("--event", default="on_submit")
    parser.add_argument("--payload", default="{}")
    args = parser.parse_args()

    payload = json.loads(args.payload)
    asyncio.run(preview(args.doctype, args.event, payload))


if __name__ == "__main__":
    main()
