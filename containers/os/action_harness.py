"""
OS Action Harness — run ad-hoc ERPNext commands without full Temporal workflow.

Usage:
    python -m containers.os.action_harness --intent "create sales order for Acme" --preview-only
    python -m containers.os.action_harness --intent "submit BOM BOM-FG-001" --confirm
    python -m containers.os.action_harness --fixture dev_fixtures/action_request.json --confirm

Pipeline: Clarity (extract_intent) → Plan → Payload → confirmation preview → optional execute.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

log = logging.getLogger("action_harness")


def _install_fake_activity_context() -> None:
    try:
        import temporalio.activity as _ta

        class _FakeActivity:
            logger = log

            @staticmethod
            def heartbeat(*args, **kwargs):
                pass

        if not getattr(_ta, "_f3next_harness_patched", False):
            _ta.logger = log
            _ta.heartbeat = _FakeActivity.heartbeat
            _ta._f3next_harness_patched = True
    except ImportError:
        pass


def _build_confirmation_preview(
    intent_dict: dict,
    plan: dict,
    payload_bundle: dict,
) -> dict[str, Any]:
    from shared.erp_policies.action_risk import (
        build_confirmation_preview as _is_preview,
        classify_action_risk,
        requires_confirmation,
    )

    steps = plan.get("steps") or []
    warnings: list[str] = []
    high_risk: list[str] = []

    for step in steps:
        dt = step.get("doctype", "")
        action = step.get("action", "create")
        tier = classify_action_risk(dt, action, context="os")
        if tier in ("high", "critical"):
            high_risk.append(dt)
            warnings.append(f"{action.title()} {dt} — {tier} risk")
        if requires_confirmation(dt, action, context="os"):
            warnings.append(f"Confirmation required: {action} {dt}")

    preview_steps = [
        {
            "doctype": s.get("doctype"),
            "action": s.get("action"),
            "records": 1,
            "risk_tier": classify_action_risk(str(s.get("doctype", "")), str(s.get("action", "create")), context="os"),
        }
        for s in steps
    ]

    return {
        "intent_id": intent_dict.get("intent_id"),
        "target_doctype": intent_dict.get("target_doctype"),
        "action": intent_dict.get("action"),
        "requires_confirmation": bool(high_risk) or plan.get("requires_confirmation", False),
        "high_risk_doctypes": sorted(set(high_risk)),
        "warnings": warnings,
        "plan_steps": len(steps),
        "payload_steps": len(payload_bundle.get("steps") or []),
        "message": (
            f"About to {intent_dict.get('action', 'execute')} "
            f"{intent_dict.get('target_doctype', 'document')} "
            f"({len(steps)} step(s))."
            + (" Financial/high-risk actions — review before confirming." if high_risk else "")
        ),
        "create_steps": preview_steps,
    }


async def _resolve_adapter(project_id: str) -> tuple[str, Any]:
    from shared.database.db import AsyncSessionLocal
    from shared.models.core import Project
    from shared.erp_adapters.registry import get_adapter
    from sqlalchemy import select
    import uuid

    base_url = ""
    api_key = ""
    api_secret = ""
    async with AsyncSessionLocal() as db:
        stmt = select(Project).where(Project.id == uuid.UUID(project_id))
        res = await db.execute(stmt)
        project = res.scalar_one_or_none()
        if project and project.deployment_details:
            details = project.deployment_details
            base_url = (details.get("site_url") or "").rstrip("/")
            api_key = details.get("api_key", "")
            api_secret = details.get("api_secret", "")

    if not base_url:
        raise RuntimeError("Project deployment_details missing site_url")

    adapter = get_adapter({
        "erp_type": "erpnext",
        "erp_url": base_url,
        "api_key": api_key,
        "api_secret": api_secret,
        "allow_insecure_ssl": True,
    })
    return base_url, adapter


async def _execute_payload_steps(adapter, payload_bundle: dict, plan: dict) -> dict:
    from containers.os.execution_agent.activities import execute_command

    context = {"erp_credentials": {
        "erp_url": adapter._profile.get("erp_url", ""),
        "api_key": adapter._profile.get("api_key", ""),
        "api_secret": adapter._profile.get("api_secret", ""),
        "verify_ssl": adapter._profile.get("verify_ssl", True),
        "allow_insecure_ssl": adapter._profile.get("allow_insecure_ssl", True),
    }}
    return await execute_command(payload_bundle, plan, context)


async def run_action_harness(
    *,
    prompt: str,
    project_id: str,
    erp_type: str = "erpnext",
    preview_only: bool = True,
    confirm: bool = False,
) -> dict[str, Any]:
    _install_fake_activity_context()

    from containers.os.clarity_agent.activities import extract_intent
    from containers.os.command_planner.activities import plan_command
    from containers.os.payload_generator.activities import generate_payload

    intent_dict = await extract_intent({
        "prompt": prompt,
        "erp_type": erp_type,
        "project_id": project_id,
        "session_context": [],
        "clarifications": [],
    })

    context = {"company_profile": {}, "cvs": {}, "project_id": project_id}
    plan = await plan_command({"intent_dict": intent_dict, "context": context})
    payload_bundle = await generate_payload({
        "plan": plan,
        "context": context,
        "intent_dict": intent_dict,
    })

    preview = _build_confirmation_preview(intent_dict, plan, payload_bundle)
    output: dict[str, Any] = {
        "status": "preview",
        "intent": intent_dict,
        "plan": plan,
        "payload_preview": payload_bundle,
        "confirmation_preview": preview,
    }

    if preview_only and not confirm:
        log.info("Preview only — no ERPNext writes. Use --confirm to execute.")
        return output

    if preview.get("requires_confirmation") and not confirm:
        output["status"] = "awaiting_confirmation"
        log.warning("Confirmation required. Re-run with --confirm to execute.")
        return output

    base_url, adapter = await _resolve_adapter(project_id)
    log.info("Executing against %s ...", base_url)
    exec_results = await _execute_payload_steps(adapter, payload_bundle, plan)
    output["status"] = "executed" if exec_results.get("success") else "failed"
    output["execution_results"] = exec_results
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="OS Action Harness — ad-hoc ERPNext commands")
    parser.add_argument("--intent", default=None, help="Natural language ERP command")
    parser.add_argument("--fixture", default=None, help="JSON fixture with prompt/project_id")
    parser.add_argument("--project-id", default=None, help="Project UUID (overrides fixture)")
    parser.add_argument("--preview-only", action="store_true", default=True,
                        help="Build plan/payload preview without writes (default)")
    parser.add_argument("--confirm", action="store_true",
                        help="Execute after preview (required for high-risk actions)")
    parser.add_argument("--output", default=None, help="Write JSON result to file")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  │  %(message)s",
        datefmt="%H:%M:%S",
    )

    fixture: dict = {}
    if args.fixture:
        with open(args.fixture, encoding="utf-8") as f:
            fixture = json.load(f)

    prompt = args.intent or fixture.get("prompt") or fixture.get("intent")
    project_id = args.project_id or fixture.get("project_id")
    if not prompt:
        parser.error("Provide --intent or a fixture with 'prompt'")
    if not project_id:
        parser.error("Provide --project-id or fixture with 'project_id'")

    preview_only = not args.confirm
    result = asyncio.run(run_action_harness(
        prompt=prompt,
        project_id=project_id,
        preview_only=preview_only,
        confirm=args.confirm,
    ))

    result_json = json.dumps(result, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(result_json, encoding="utf-8")
        log.info("Wrote result to %s", args.output)
    else:
        print(result_json)


if __name__ == "__main__":
    main()
